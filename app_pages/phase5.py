import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase5 import render_phase5


render_phase_page(
    st,
    PHASE_SPECS["phase5"],
    lambda: render_phase5(st),
)
