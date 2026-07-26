import streamlit as st

from app import render_phase4
from ui.components import render_phase_page
from ui.constants import PHASE_SPECS


render_phase_page(st, PHASE_SPECS["phase4"], render_phase4)
