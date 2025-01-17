"""Nautobot App Livedate view for results."""

# filepath: livedata/template_content.py

from nautobot.apps.ui import DistinctViewTab, TemplateExtension


class LivedataInterfaceExtraTabs(TemplateExtension):  # pylint: disable=abstract-method
    """Add a tab to the interface detail view."""

    model = "dcim.interface"

    object_detail_tabs = (
        DistinctViewTab(
            weight=100,
            tab_id="interface_livedata_tab",
            label="Live Data",
            url_name="plugins:nautobot_app_livedata:interface_detail_tab",
        ),
    )


template_extensions = [LivedataInterfaceExtraTabs]
