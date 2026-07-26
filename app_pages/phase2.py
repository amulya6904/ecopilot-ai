import streamlit as st

from app import render_phase2
from ui.components import render_phase_page
from ui.constants import PHASE_SPECS


render_phase_page(st, PHASE_SPECS["phase2"], render_phase2)
