import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import numpy as np
from PIL import Image

# UI Configuration
st.set_page_config(page_title="PDF OCR Tool", layout="centered")

# The UI you requested
st.markdown("<h1 style='text-align: center;'>Send documents to x@y.</h1>", unsafe_allow_html=True)
st.write("---")

# File Uploader (Simulating the "receipt" of a document)
uploaded_file = st.file_uploader("Upload your PDF here", type=["pdf"])

if uploaded_file is not None:
    with st.spinner('Extracting text...'):
        # Convert PDF to list of images
        images = convert_from_bytes(uploaded_file.read())
        
        full_text = ""
        for i, image in enumerate(images):
            # Perform OCR on each page
            text = pytesseract.image_to_string(image)
            full_text += f"--- Page {i+1} ---\n{text}\n\n"
        
        # Display the info onto the screen
        st.subheader("Extracted Information:")
        st.text_area(label="OCR Result", value=full_text, height=400)
        
        st.success("OCR Process Complete!")
