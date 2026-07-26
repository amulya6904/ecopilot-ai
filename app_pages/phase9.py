import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase9 import render_phase9


render_phase_page(
    st,
    PHASE_SPECS["phase9"],
    lambda: render_phase9(st),
)
