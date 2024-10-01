import streamlit as st


def main():
    st.header("ChatBot🤖")
    st.subheader("Enter any question regarding the uploaded File..")

    with st.sidebar:
        st.title("Chat With PDFs")
        pdfs = st.file_uploader("Upload your PDF and click submit",type = "pdf",accept_multiple_files=True)
        if st.button("Submit"):
            st.success("File Uploaded ✔")
    
    if question:= st.chat_input("Enter a question.."):
        with st.chat_message("user"):
            st.markdown(question)
            expander = st.expander("See explanation")
            expander.write(""" The chatrt us hill whk """)
        
        st.session_state['chat_history'].append({"role":"user","question":question})

if __name__ =='__main__':
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    main()