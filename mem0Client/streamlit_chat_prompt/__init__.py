import logging
import os
from typing import List, Optional, Union, Literal

import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel

# Create a _RELEASE constant. We'll set this to False while we're developing
# the component, and True when we're ready to package and distribute it.
# (This is, of course, optional - there are innumerable ways to manage your
# release process.)
_RELEASE = True

logger = logging.getLogger("streamlit_chat_prompt")
logger.setLevel(logging.WARN)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

# set default limits for file uploads
DEFAULT_IMAGE_FILE_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_IMAGE_PIXEL_DIMENSION = 8000
DEFAULT_IMAGE_COUNT = 20
DEFAULT_DOCUMENT_FILE_SIZE = 4.5 * 1024 * 1024  # 4.5MB
DEFAULT_DOCUMENT_COUNT = 5

# Declare a Streamlit component. `declare_component` returns a function
# that is used to create instances of the component. We're naming this
# function "_component_func", with an underscore prefix, because we don't want
# to expose it directly to users. Instead, we will create a custom wrapper
# function, below, that will serve as our component's public API.

# It's worth noting that this call to `declare_component` is the
# *only thing* you need to do to create the binding between Streamlit and
# your component frontend. Everything else we do in this file is simply a
# best practice.

if not _RELEASE:
    _component_func = components.declare_component(
        # We give the component a simple, descriptive name ("my_component"
        # does not fit this bill, so please choose something better for your
        # own component :)
        "streamlit_chat_prompt",
        # Pass `url` here to tell Streamlit that the component will be served
        # by the local dev server that you run via `npm run start`.
        # (This is useful while your component is in development.)
        url="http://localhost:3001",
    )
else:
    # When we're distributing a production version of the component, we'll
    # replace the `url` param with `path`, and point it to the component's
    # build directory:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component(
        "streamlit_chat_prompt", path=build_dir
    )


class FileData(BaseModel):
    type: str
    format: str
    data: str
    name: Optional[str] = None
    size: Optional[int] = None
    file_type: Literal['image', 'pdf', 'markdown', 'audio'] = None  # For internal type tracking

    @property
    def is_image(self) -> bool:
        return self.type.startswith('image/')

    @property
    def is_document(self) -> bool:
        return not self.is_image


class PromptReturn(BaseModel):
    text: Optional[str] = None
    files: Optional[List[FileData]] = None
    uuid: Optional[str] = None

    @property
    def images(self) -> List[FileData]:
        """Maintain backward compatibility for images access"""
        if not self.files:
            return []
        return [f for f in self.files if f.is_image]

    @property
    def documents(self) -> List[FileData]:
        """Helper to get non-image files"""
        if not self.files:
            return []
        return [f for f in self.files if f.is_document]


__all__ = ["prompt", "PromptReturn", "FileData",
           "DEFAULT_IMAGE_FILE_SIZE", "DEFAULT_IMAGE_PIXEL_DIMENSION", "DEFAULT_IMAGE_COUNT",
           "DEFAULT_DOCUMENT_FILE_SIZE", "DEFAULT_DOCUMENT_COUNT"]

_prompt_main_singleton_key: Optional[str] = None


def pin_bottom(key: str):
    # pin prompt to bottom of main area
    st.markdown(
        f"""
        <style>
        .st-key-{key}"""
        + """ {
            position: fixed;
            bottom: 1rem;
            z-index: 1000;
        }

        /* Main content area */
        section[data-testid="stMain"] {
            margin-bottom: 100px;  /* Make room for the fixed component */
        }

        /* When sidebar is expanded */
        """
        + f""".sidebar-expanded .st-key-{key}"""
        + """ {
            left: calc((100% - 245px) / 2 + 245px);  /* 245px is default sidebar width */
            width: calc(min(800px, 100% - 245px - 2rem)) !important;
            transform: translateX(-50%);
        }

        /* When sidebar is collapsed */
        """
        + f""".sidebar-collapsed .st-key-{key}"""
        + """ {
            left: 50%;
            width: calc(min(800px, 100% - 2rem)) !important;
            transform: translateX(-50%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def prompt(
    name: str,
    key: str,
    placeholder="Hi there! What should we talk about?",
    default: Optional[Union[str, PromptReturn]] = None,
    main_bottom: bool = True,
    max_image_file_size: int = DEFAULT_IMAGE_FILE_SIZE,
    max_image_pixel_dimension: int = DEFAULT_IMAGE_PIXEL_DIMENSION,
    max_image_count: int = DEFAULT_IMAGE_COUNT,
    max_document_file_size: int = DEFAULT_DOCUMENT_FILE_SIZE,
    max_document_count: int = DEFAULT_DOCUMENT_COUNT,
    disabled: bool = False,
    log_level: str = "warn",
    enable_clipboard_inspector: bool = False,
) -> Optional[PromptReturn]:
    """Create a chat-like prompt input at the bottom of the page.

    Args:
        name (str): A unique identifier for this prompt instance.
        key (str): Used to ensure only a single prompt can be created.
        placeholder (str, optional): The placeholder text shown in the input field. Defaults to "Hi there! What should we talk about?".
        default (Union[str, PromptReturn], optional): Default value for the prompt.
            Can be either a string (text only) or PromptReturn object (text and images). Defaults to None.
        main_bottom (bool, optional): Whether to position at bottom of main area. Defaults to True.
        max_image_file_size (int, optional): Maximum size of uploaded images in bytes. Defaults to 5MB.
        max_image_pixel_dimension (int, optional): Maximum pixel dimension of uploaded images. Defaults to 8000.
        max_image_count (int, optional): Maximum number of images allowed. Defaults to 20.
        max_document_file_size (int, optional): Maximum size of uploaded documents in bytes. Defaults to 4.5MB.
        max_document_count (int, optional): Maximum number of documents allowed. Defaults to 5.
        disabled (bool, optional): Whether the prompt input is disabled. Defaults to False.
        log_level (str, optional): Logging level for the component. Defaults to "warn".
        enable_clipboard_inspector (bool, optional): Whether to enable clipboard inspector. Defaults to False.

    Returns:
        Optional[PromptReturn]: Returns a PromptReturn object containing the text
        and files entered by the user when submitted, or None if nothing submitted yet.
        The PromptReturn object has these fields:
            - text (Optional[str]): The text entered by the user
            - files (Optional[List[FileData]]): List of all files uploaded by the user
            - images (Optional[List[FileData]]): List of images only (convenience property)
            - documents (Optional[List[FileData]]): List of non-image files (convenience property)
    """
    logger.debug(
        f"Creating prompt: name={name}, key={key}, placeholder={placeholder}, default={default}, main_bottom={main_bottom}"
    )
    # Convert string default to PromptReturn if needed
    if isinstance(default, str):
        default = PromptReturn(text=default)

    if f"chat_prompt_{key}_prev_uuid" not in st.session_state:
        st.session_state[f"chat_prompt_{key}_prev_uuid"] = None

    # Convert images to base64 strings if present in default
    default_value = None
    if default:
        processed_files = []

        # Handle legacy images
        if default.images:
            for img in default.images:
                processed_files.append(
                    {
                        "data": f"data:{img.type};{img.format},{img.data}",
                        "type": img.type,
                        "name": "image",
                    }
                )

        # Handle new files
        if default.files:
            for file in default.files:
                processed_files.append(
                    {
                        "data": f"data:{file.type};{file.format},{file.data}",
                        "type": file.type,
                        "name": getattr(file, "name", None) or "file",
                    }
                )

        default_value = {
            "text": default.text or "",
            "files": processed_files,
            "uuid": None,  # No UUID for default value
        }

    if main_bottom:
        global _prompt_main_singleton_key

        if _prompt_main_singleton_key and _prompt_main_singleton_key != key:
            raise RuntimeError(
                "Multiple prompt instances detected. Only one prompt component can be used per Streamlit app. "
                "Please ensure you're only creating a single prompt instance in your application."
            )
        _prompt_main_singleton_key = key

        pin_bottom(key)

    image_file_upload_limits = {
        "max_size_in_bytes": max_image_file_size,
        "max_count": max_image_count,
        "max_dimension_in_pixels": max_image_pixel_dimension,
    }

    document_file_upload_limits = {
        "max_size_in_bytes": max_document_file_size,
        "max_count": max_document_count,
    }

    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # "default" is a special argument that specifies the initial return
    # value of the component before the user has interacted with it.
    component_value = _component_func(
        name=name,
        placeholder=placeholder,
        default=default_value,
        key=key,
        disabled=disabled,
        image_file_upload_limits=image_file_upload_limits,
        document_file_upload_limits=document_file_upload_limits,
        debug=log_level,
        clipboard_inspector_enabled=enable_clipboard_inspector,
    )
    logger.debug(f"prompt value: {component_value}")

    if (
        component_value
        and component_value["uuid"] != st.session_state[f"chat_prompt_{key}_prev_uuid"]
        and component_value["uuid"] is not None
    ):
        # we have a new prompt return
        st.session_state[f"chat_prompt_{key}_prev_uuid"] = component_value["uuid"]
        processed_files = []
        processed_images = []  # Separate list for images

        # Process any files
        if component_value.get("files"):
            for file_data in component_value["files"]:
                if isinstance(file_data, str):  # If it's a data URL string
                    parts = file_data.split(";")
                    file_type = parts[0].split(":")[1]
                    file_format = parts[1].split(",")[0]
                    file_data_content = parts[1].split(",")[1]

                    file = FileData(
                        type=file_type,
                        format=file_format,
                        data=file_data_content,
                        name=None
                    )

                    processed_files.append(file)

                    # If it's an image, also add to images list
                    if file_type.startswith('image/'):
                        processed_images.append(FileData(
                            type=file_type,
                            format=file_format,
                            data=file_data_content,
                            name=None
                        ))

                else:  # If it's already a dictionary
                    file = FileData(**file_data)
                    processed_files.append(file)

                    # If it's an image, also add to images list
                    if file.type.startswith('image/'):
                        processed_images.append(FileData(
                            type=file.type,
                            format=file.format,
                            data=file.data,
                            name=getattr(file, 'name', None)
                        ))

        if not processed_files and not component_value.get("text"):
            return None

        # Create return object with both files and images
        return PromptReturn(
            text=component_value.get("text"),
            files=processed_files,
            uuid=component_value.get("uuid")
        )
    else:
        return None
