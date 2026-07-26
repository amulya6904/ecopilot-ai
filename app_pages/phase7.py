import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase7 import render_phase7


render_phase_page(
    st,
    PHASE_SPECS["phase7"],
    lambda: render_phase7(st),
)
