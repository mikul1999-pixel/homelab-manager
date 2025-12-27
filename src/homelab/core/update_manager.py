from typing import Dict, List, Optional
from datetime import datetime
import docker
from homelab.core.models import VersionHistory, ImageTag
from homelab.core.docker_manager import DockerManager
from homelab.core.version_tracker import VersionTracker
from homelab.core.update_checker import UpdateChecker

class UpdateManager:
    """Perform updates to container images"""

    def __init__(self, session):
        self.session = session
        self.tracker = VersionTracker(session)
        self.checker = UpdateChecker(session)
        self.docker_manager = DockerManager()

    def update_container(self, container_name: str, on_event=None) -> Optional[Dict]:
        """Execute an image update if available"""

        def emit(msg):
            if on_event:
                on_event(msg)

        # Step 1: Snapshot current version
        emit("Creating snapshot of current version...")
        before_snapshot = self.tracker.create_snapshot(container_name)
        emit(f"Snapshot created (ID: {before_snapshot.id})")

        # Step 2: Check for update availability
        update_info = self.checker.check_for_update(container_name)
        current_digest = update_info["current_digest"]
        latest_digest = update_info["latest_digest"]

        # Step 3: Get container details
        details = self.docker_manager.get_container_details(container_name)
        image_to_use = self.tracker.get_version_name(container_name)
        details['image'] = image_to_use

        # Step 4: Execute update
        emit("Updating container to new version...")
        try:
            self.docker_manager.recreate_container(
                name=container_name,
                image=details["image"],
                config=details,
                image_digest=latest_digest,
            )
            emit("Container updated successfully")
        except Exception as e:
            emit(f"Update failed: {e}")
            emit(f"Rolling back to snapshot {before_snapshot.id}...")

            try:
                self.tracker.rollback_container(container_name, before_snapshot.id)
                emit("Rollback successful")
            except Exception as rollback_error:
                emit(f"Rollback failed: {rollback_error}")
                return {
                    "updated": False,
                    "reason": "rollback_failed",
                    "error": str(rollback_error),
                }

            return {
                "updated": False,
                "reason": "update_failed",
                "error": str(e),
            }

        # Step 5: Snapshot new version
        emit("Creating snapshot of new version...")
        new_details = self.docker_manager.get_container_details(container_name)

        after_snapshot = VersionHistory(
            container_name=container_name,
            image_version=details['image'],
            image_digest=new_details.get("image_digest"),
            image_id=new_details.get("image_id"),
            config_snapshot=new_details,
            action="update",
        )

        self.session.add(after_snapshot)
        self.session.commit()
        emit(f"New version snapshot created (ID: {after_snapshot.id})")

        return {
            "updated": True,
            "before_snapshot": before_snapshot.id,
            "after_snapshot": after_snapshot.id,
            "latest_digest": latest_digest,
        }
