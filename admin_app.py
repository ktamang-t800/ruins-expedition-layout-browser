from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

from database import (
    init_db,
    add_pattern_group,
    get_all_pattern_groups,
    get_next_group_name,
    add_layout,
    get_layouts_by_group,
    get_all_layouts,
    delete_layout,
    delete_pattern_group,
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CROP_DIR = Path("uploads") / "top_crops"
CROP_DIR.mkdir(parents=True, exist_ok=True)

GROUP_DIR = Path("uploads") / "pattern_groups"
GROUP_DIR.mkdir(parents=True, exist_ok=True)

init_db()

st.set_page_config(
    page_title="Ruins Expedition Layout Browser",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Ruins Expedition Layout Browser")
st.caption("Choose a top pattern and view all saved layouts.")


if "admin_upload_key" not in st.session_state:
    st.session_state["admin_upload_key"] = 0

if "last_save_message" not in st.session_state:
    st.session_state["last_save_message"] = ""


def save_image(image: Image.Image, folder: Path, original_filename: str, prefix="image") -> str:
    safe_name = original_filename.replace(" ", "_")
    safe_name = safe_name.replace("/", "_").replace("\\", "_")

    if not safe_name.lower().endswith((".png", ".jpg", ".jpeg")):
        safe_name = f"{safe_name}.png"

    file_path = folder / f"{prefix}_{safe_name}"

    counter = 1
    while file_path.exists():
        file_path = folder / f"{prefix}_{counter}_{safe_name}"
        counter += 1

    image.convert("RGB").save(file_path)
    return str(file_path)


def delete_file_if_exists(path_text):
    if not path_text:
        return

    try:
        file_path = Path(path_text)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def crop_top_pattern(image: Image.Image) -> Image.Image:
    width, height = image.size

    left = int(width * 0.12)
    right = int(width * 0.88)
    top = int(height * 0.18)
    bottom = int(height * 0.31)

    return image.crop((left, top, right, bottom))


def open_image_safely(path):
    try:
        return Image.open(path).convert("RGB")
    except FileNotFoundError:
        return None
    except UnidentifiedImageError:
        return None
    except Exception:
        return None


def save_layout_under_group(group_id, image, top_crop, original_filename, stage_number, notes):
    screenshot_path = save_image(
        image=image,
        folder=UPLOAD_DIR,
        original_filename=original_filename,
        prefix="db",
    )

    top_crop_path = save_image(
        image=top_crop,
        folder=CROP_DIR,
        original_filename=original_filename,
        prefix="top",
    )

    add_layout(
        group_id=group_id,
        screenshot_path=screenshot_path,
        top_crop_path=top_crop_path,
        image_hash="manual",
        stage_number=stage_number,
        notes=notes,
    )


def create_new_pattern_and_save(image, top_crop, original_filename, stage_number, notes):
    new_group_name = get_next_group_name()

    representative_crop_path = save_image(
        image=top_crop,
        folder=GROUP_DIR,
        original_filename=f"{new_group_name}.png",
        prefix="group",
    )

    group_id = add_pattern_group(
        group_name=new_group_name,
        representative_crop_path=representative_crop_path,
        representative_hash="manual",
    )

    save_layout_under_group(
        group_id=group_id,
        image=image,
        top_crop=top_crop,
        original_filename=original_filename,
        stage_number=stage_number,
        notes=notes,
    )

    return group_id


def after_successful_save(message):
    st.session_state["last_save_message"] = message
    st.session_state["admin_upload_key"] += 1
    st.rerun()


def display_layout_grid(layouts, allow_delete=False, compact=True, key_prefix="layout"):
    if not layouts:
        st.info("No saved layouts here yet.")
        return

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
                st.markdown(f"**Layout #{layout_id}**")

                if stage_number:
                    st.caption(stage_number)

                full_img = open_image_safely(screenshot_path)
                if full_img:
                    st.image(full_img, width=210 if compact else 260)
                else:
                    st.warning("Screenshot missing.")

                if notes:
                    st.caption(notes)

                if allow_delete:
                    with st.expander("Delete layout"):
                        st.warning("Deletes only this layout.")

                        confirm = st.checkbox(
                            "Confirm delete",
                            key=f"{key_prefix}_confirm_delete_layout_{layout_id}",
                        )

                        if st.button(
                            "Delete",
                            key=f"{key_prefix}_delete_layout_{layout_id}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            if confirm:
                                deleted_files = delete_layout(layout_id)

                                if deleted_files:
                                    screenshot_to_delete, crop_to_delete = deleted_files
                                    delete_file_if_exists(screenshot_to_delete)
                                    delete_file_if_exists(crop_to_delete)

                                st.success("Layout deleted.")
                                st.rerun()
                            else:
                                st.error("Tick confirm first.")


def display_user_patterns(groups):
    st.subheader("Choose Top Pattern")

    if not groups:
        st.info("No top patterns saved yet. Add database screenshots first.")
        return

    cols = st.columns(4)

    for index, group in enumerate(groups, start=1):
        group_id, group_name, representative_crop_path, representative_hash, created_at = group

        with cols[(index - 1) % 4]:
            with st.container(border=True):
                img = open_image_safely(representative_crop_path)

                if img:
                    st.image(img, width=220)
                else:
                    st.warning("Pattern image missing.")

                if st.button(
                    "Show Layouts",
                    key=f"user_show_group_{group_id}",
                    use_container_width=True,
                ):
                    st.session_state["selected_group_id"] = group_id
                    st.session_state["selected_group_label"] = f"Selected Top Pattern"
                    st.rerun()


tab_user, tab_admin, tab_patterns, tab_browse = st.tabs(
    [
        "🔍 User View",
        "➕ Admin Add",
        "🧩 Manage Top Patterns",
        "📚 Browse All Layouts",
    ]
)


with tab_user:
    st.header("User View")

    groups = get_all_pattern_groups()
    display_user_patterns(groups)

    st.divider()

    selected_group_id = st.session_state.get("selected_group_id")

    if selected_group_id:
        st.header("Layouts for Selected Top Pattern")
        matched_layouts = get_layouts_by_group(selected_group_id)
        st.success(f"{len(matched_layouts)} saved layout(s).")
        display_layout_grid(
            matched_layouts,
            allow_delete=False,
            compact=True,
            key_prefix="user",
        )
    else:
        st.info("Click a top pattern above to display saved layouts.")


with tab_admin:
    st.header("Admin: Add Database Screenshot")

    if st.session_state.get("last_save_message"):
        st.success(st.session_state["last_save_message"])
        st.session_state["last_save_message"] = ""

    db_file = st.file_uploader(
        "Upload database screenshot",
        type=["png", "jpg", "jpeg"],
        key=f"admin_upload_{st.session_state['admin_upload_key']}",
    )

    stage_number = st.text_input(
        "Layout label optional",
        placeholder="Example: Layout 1, Layout 2, Stage 12",
        key=f"stage_number_{st.session_state['admin_upload_key']}",
    )

    notes = st.text_area(
        "Notes optional",
        placeholder="Example: Same top pattern, different layout.",
        key=f"notes_{st.session_state['admin_upload_key']}",
    )

    if db_file:
        image = Image.open(db_file).convert("RGB")
        top_crop = crop_top_pattern(image)

        st.subheader("Preview Before Saving")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.write("**Detected Top Pattern**")
            st.image(top_crop, width=300)

        with col2:
            st.write("**Full Screenshot Preview**")
            st.image(image, width=360)

        st.divider()

        confirm_save = st.checkbox(
            "I checked the detected top pattern and want to save this screenshot.",
            key=f"admin_confirm_save_{st.session_state['admin_upload_key']}",
        )

        st.subheader("Choose Where to Save")

        col_new, col_existing = st.columns([1, 3])

        with col_new:
            with st.container(border=True):
                st.markdown("### New Top Pattern")
                st.image(top_crop, width=220)
                st.caption("Use this if this top pattern is not already listed.")

                if st.button(
                    "Create New Pattern & Save",
                    type="primary",
                    use_container_width=True,
                    key=f"create_new_and_save_{st.session_state['admin_upload_key']}",
                ):
                    if not confirm_save:
                        st.error("Please tick the confirmation checkbox first.")
                    else:
                        create_new_pattern_and_save(
                            image=image,
                            top_crop=top_crop,
                            original_filename=db_file.name,
                            stage_number=stage_number,
                            notes=notes,
                        )

                        after_successful_save("Saved successfully under a new top pattern. You can upload the next screenshot now.")

        with col_existing:
            st.markdown("### Existing Top Patterns")

            groups = get_all_pattern_groups()

            if not groups:
                st.info("No existing top patterns yet. Create a new top pattern first.")
            else:
                pattern_cols = st.columns(4)

                for index, group in enumerate(groups, start=1):
                    group_id, group_name, representative_crop_path, representative_hash, created_at = group
                    layouts = get_layouts_by_group(group_id)

                    with pattern_cols[(index - 1) % 4]:
                        with st.container(border=True):
                            img = open_image_safely(representative_crop_path)

                            if img:
                                st.image(img, width=190)
                            else:
                                st.warning("Pattern image missing.")

                            st.caption(f"{len(layouts)} saved layout(s)")

                            if st.button(
                                "Save Here",
                                key=f"save_here_{group_id}_{st.session_state['admin_upload_key']}",
                                use_container_width=True,
                            ):
                                if not confirm_save:
                                    st.error("Please tick the confirmation checkbox first.")
                                else:
                                    save_layout_under_group(
                                        group_id=group_id,
                                        image=image,
                                        top_crop=top_crop,
                                        original_filename=db_file.name,
                                        stage_number=stage_number,
                                        notes=notes,
                                    )

                                    after_successful_save("Saved successfully under the selected existing top pattern. You can upload the next screenshot now.")


with tab_patterns:
    st.header("Manage Top Patterns")

    groups = get_all_pattern_groups()

    if not groups:
        st.info("No top patterns saved yet.")
    else:
        st.success(f"Total top patterns: {len(groups)}")

        for index, group in enumerate(groups, start=1):
            group_id, group_name, representative_crop_path, representative_hash, created_at = group
            layouts = get_layouts_by_group(group_id)

            with st.container(border=True):
                col_pattern, col_details = st.columns([1, 3])

                with col_pattern:
                    st.subheader("Top Pattern")
                    st.caption(f"{len(layouts)} saved layout(s)")

                    img = open_image_safely(representative_crop_path)
                    if img:
                        st.image(img, width=240)
                    else:
                        st.warning("Pattern image missing.")

                    with st.expander("Delete entire top pattern"):
                        st.warning("This deletes this top pattern and all layouts under it.")

                        confirm_group_delete = st.checkbox(
                            "Confirm delete entire top pattern",
                            key=f"confirm_delete_group_{group_id}",
                        )

                        if st.button(
                            "Delete Top Pattern",
                            key=f"delete_group_{group_id}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            if confirm_group_delete:
                                group_file, layout_files = delete_pattern_group(group_id)

                                if group_file:
                                    delete_file_if_exists(group_file[0])

                                for screenshot_to_delete, crop_to_delete in layout_files:
                                    delete_file_if_exists(screenshot_to_delete)
                                    delete_file_if_exists(crop_to_delete)

                                if st.session_state.get("selected_group_id") == group_id:
                                    st.session_state.pop("selected_group_id", None)
                                    st.session_state.pop("selected_group_label", None)

                                st.success("Top pattern deleted.")
                                st.rerun()
                            else:
                                st.error("Tick confirm first.")

                with col_details:
                    st.markdown("### Layouts under this top pattern")
                    display_layout_grid(
                        layouts,
                        allow_delete=True,
                        compact=True,
                        key_prefix=f"manage_{group_id}",
                    )


with tab_browse:
    st.header("Browse All Saved Layouts")

    all_layouts = get_all_layouts()

    if not all_layouts:
        st.info("No layouts saved yet.")
    else:
        st.success(f"Total saved layouts: {len(all_layouts)}")
        display_layout_grid(
            all_layouts,
            allow_delete=True,
            compact=True,
            key_prefix="browse",
        )