"""Cloudinary service for file uploads and management."""

import os
import tempfile
from typing import Optional, Tuple
import cloudinary
import cloudinary.uploader
from app.config import get_settings

settings = get_settings()


def configure_cloudinary():
    """Configure Cloudinary with credentials from settings."""
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
        
        # Extract public_id from the URL
        # Cloudinary URL format: https://res.cloudinary.com/cloud_name/raw/upload/folder/public_id
        parts = public_url.split("/")
        if "upload" in parts:
            upload_index = parts.index("upload")
            # Everything after 'upload' is the public_id (including folder)
            public_id = "/".join(parts[upload_index + 1:])
            
            # Remove file extension if present
            public_id = os.path.splitext(public_id)[0]
            
            result = cloudinary.uploader.destroy(public_id, resource_type="raw")
            return result.get("result") == "ok"
        
        return False
    except Exception as e:
        print(f"Error deleting from Cloudinary: {str(e)}")
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
