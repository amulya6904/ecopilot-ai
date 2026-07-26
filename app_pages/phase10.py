import streamlit as st

from ui.components import render_phase_page
from ui.constants import PHASE_SPECS
from ui.phase10 import render_phase10


render_phase_page(
    st,
    PHASE_SPECS["phase10"],
    lambda: render_phase10(st),
)
