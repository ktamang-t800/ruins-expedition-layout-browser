from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

from database import (
    init_db,
    get_all_pattern_groups,
    get_layouts_by_group,
)


init_db()

st.set_page_config(
    page_title="Ruins Expedition Layout Browser",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Ruins Expedition Layout Browser")
st.caption("Choose a top pattern to view all saved layouts.")


def open_image_safely(path):
    try:
        return Image.open(path).convert("RGB")
    except FileNotFoundError:
        return None
    except UnidentifiedImageError:
        return None
    except Exception:
        return None


def display_layouts(layouts):
    if not layouts:
        st.info("No saved layouts under this top pattern yet.")
        return

    st.success(f"{len(layouts)} saved layout(s) found.")

    cols = st.columns(4)

    for index, row in enumerate(layouts):
        (
            layout_id,
            group_id,
            group_name,
            screenshot_path,
            top_crop_path,
            image_hash,
            stage_number,
            notes,
            created_at,
        ) = row

        with cols[index % 4]:
            with st.container(border=True):
                if stage_number:
                    st.markdown(f"**{stage_number}**")
                else:
                    st.markdown(f"**Layout #{layout_id}**")

                full_img = open_image_safely(screenshot_path)

                if full_img:
                    st.image(full_img, width=220)
                else:
                    st.warning("Screenshot not available.")

                if notes:
                    st.caption(notes)


def display_patterns(groups):
    if not groups:
        st.info("No top patterns have been added yet.")
        return

    st.subheader("Choose Top Pattern")

    cols = st.columns(4)

    for index, group in enumerate(groups):
        group_id, group_name, representative_crop_path, representative_hash, created_at = group

        with cols[index % 4]:
            with st.container(border=True):
                img = open_image_safely(representative_crop_path)

                if img:
                    st.image(img, width=220)
                else:
                    st.warning("Pattern image not available.")

                if st.button(
                    "Show Layouts",
                    key=f"show_group_{group_id}",
                    use_container_width=True,
                ):
                    st.session_state["selected_group_id"] = group_id
                    st.rerun()


groups = get_all_pattern_groups()

display_patterns(groups)

st.divider()

selected_group_id = st.session_state.get("selected_group_id")

if selected_group_id:
    st.subheader("Saved Layouts for Selected Pattern")
    layouts = get_layouts_by_group(selected_group_id)
    display_layouts(layouts)
else:
    st.info("Click a top pattern above to view its saved layouts.")