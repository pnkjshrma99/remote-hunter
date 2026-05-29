"""Cloudinary service for file uploads and management."""

import os
import logging
import tempfile
from typing import Optional, Tuple
import cloudinary
import cloudinary.uploader
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


def cloudinary_configured() -> bool:
    """Check if Cloudinary credentials are configured."""
    return bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret)


def configure_cloudinary():
    """Configure Cloudinary with credentials from settings."""
    if not cloudinary_configured():
        return
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )


def upload_file_to_cloudinary(
    file_path: str,
    folder: str = "cvs",
    resource_type: str = "auto"
) -> Tuple[Optional[str], Optional[dict]]:
    """
    Upload a file to Cloudinary.
    
    Args:
        file_path: Path to the file to upload
        folder: Cloudinary folder to store the file in
        resource_type: Type of resource (auto, image, raw, video)
    
    Returns:
        Tuple of (public_url, upload_result) or (None, None) on failure
    """
    try:
        configure_cloudinary()
        if not cloudinary_configured():
            print("Cloudinary not configured — skipping upload")
            return None, None
        
        # Extract filename without extension for the public_id
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            public_id=name_without_ext,
            resource_type=resource_type,
            overwrite=True,
            invalidate=True
        )
        
        return result.get("secure_url"), result
    except Exception as e:
        print(f"Error uploading to Cloudinary: {str(e)}")
        return None, None


def upload_bytes_to_cloudinary(
    file_bytes: bytes,
    filename: str,
    folder: str = "cvs",
    resource_type: str = "auto"
) -> Tuple[Optional[str], Optional[dict]]:
    """
    Upload file bytes to Cloudinary.
    
    Args:
        file_bytes: File content as bytes
        filename: Original filename
        folder: Cloudinary folder to store the file in
        resource_type: Type of resource (auto, image, raw, video)
    
    Returns:
        Tuple of (public_url, upload_result) or (None, None) on failure
    """
    try:
        configure_cloudinary()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        
        try:
            # Upload the temporary file
            return upload_file_to_cloudinary(temp_file_path, folder, resource_type)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    except Exception as e:
        print(f"Error uploading bytes to Cloudinary: {str(e)}")
        return None, None


def delete_file_from_cloudinary(public_url: str) -> bool:
    """
    Delete a file from Cloudinary using its public URL.
    
    Args:
        public_url: The secure URL of the file to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        configure_cloudinary()
        if not cloudinary_configured():
            logger.warning("Cloudinary not configured — cannot delete")
            return False
        
        logger.info(f"Attempting to delete Cloudinary file: {public_url}")
        
        # Cloudinary URL format:
        # https://res.cloudinary.com/cloud_name/resource_type/upload/v123/folder/public_id.ext
        parts = public_url.split("/")
        if "upload" in parts:
            upload_index = parts.index("upload")
            
            # Extract the actual resource_type from the URL (e.g., "image", "raw", "video")
            resource_type = parts[upload_index - 1] if upload_index > 0 else "raw"
            
            # Skip the version string (e.g., "v123456") right after "upload"
            path_parts = parts[upload_index + 1:]
            if path_parts and path_parts[0].startswith("v"):
                path_parts = path_parts[1:]
            
            public_id = "/".join(path_parts)
            
            logger.info(f"Extracted public_id='{public_id}', resource_type='{resource_type}'")
            
            # Try with the full path first (extension included — Cloudinary sometimes
            # stores extension as part of public_id for raw files), then without
            candidates = {public_id, os.path.splitext(public_id)[0]}
            
            for candidate in candidates:
                for rtype in [resource_type, "image"]:
                    result = cloudinary.uploader.destroy(candidate, resource_type=rtype)
                    logger.info(f"Cloudinary destroy('{candidate}', {rtype}): {result}")
                    if result.get("result") == "ok":
                        return True
            
            return False
        
        logger.warning(f"Could not find 'upload' in URL: {public_url}")
        return False
    except Exception as e:
        logger.error(f"Error deleting from Cloudinary: {str(e)}")
        return False


def get_file_public_id(public_url: str) -> Optional[str]:
    """
    Extract the public_id from a Cloudinary public URL.
    
    Args:
        public_url: The secure URL of the file
    
    Returns:
        The public_id or None if extraction fails
    """
    try:
        parts = public_url.split("/")
        if "upload" in parts:
            upload_index = parts.index("upload")
            public_id = "/".join(parts[upload_index + 1:])
            return os.path.splitext(public_id)[0]
        return None
    except Exception:
        return None
