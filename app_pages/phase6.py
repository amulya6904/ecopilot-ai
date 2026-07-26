import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase6 import render_phase6


render_phase_page(
    st,
    PHASE_SPECS["phase6"],
    lambda: render_phase6(st),
)
