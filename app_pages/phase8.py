import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase8 import render_phase8


render_phase_page(
    st,
    PHASE_SPECS["phase8"],
    lambda: render_phase8(st),
)
