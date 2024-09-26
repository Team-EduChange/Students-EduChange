import streamlit as st

# button_style
def button_style_1():
    button_style = """
    <style>
    .stButton > button {
        width: 100%;
        height: 100px;
        font-size: 30px;
        font-weight: 700;
        font-family: 'Nanum Gothic';
    }
    </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)

def button_style_2():
    button_style = """
    <style>
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 30px;
        font-weight: 700;
        font-family: 'Nanum Gothic';
    }
    </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)


# educhange_logo
def educhange_logo():
    educhange_logo = """
        <style>
        .educhange-logo {
            font-family: 'Brush Script MT', cursive;
            font-size: 45px;
        }
        .educhange-logo span {
            color: black;
        }
        .educhange-logo .red {
            color: red;
        }
        </style>
        <div class="educhange-logo">
            &nbsp;&nbsp;&nbsp;<span class="red">E</span><span>du</span><span class="red">C</span><span>hange</span>
        </div>
    """
    st.markdown(educhange_logo, unsafe_allow_html=True)


# box_style
def box_style():
    custom_css = """
    <style>
        .box {
            border: 1px solid #d3d3d3;
            border-radius: 7px;
            padding: 13px;
            background-color: #ffffff;
            font-family: Arial, sans-serif;
            font-size: 16px;
            color: #333;
            margin-bottom: 50px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)