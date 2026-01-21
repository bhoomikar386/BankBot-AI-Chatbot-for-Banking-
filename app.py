import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from database.db import init_db, get_conn
from database.bank_crud import create_account, get_account, transfer_money
from database.security import verify_password
from dotenv import load_dotenv
from dialogue_manager.dialogue_handler import DialogueManager # Make sure this import is here

# Load environment variables (.env)
load_dotenv()

# Initialize Database
init_db()


# --- REALISTIC UI CONFIG ---
st.set_page_config(page_title="BHOOMIKA R", layout="wide", page_icon="💎")

def add_bg_and_style():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
                        url("https://cms-resources.groww.in/uploads/TAX_SLAB_2025_06_03_T112143_053_11zon_980594947c.jpg");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }
        .premium-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
            margin-bottom: 20px;
        }
        .stTextInput input, .stNumberInput input {
            background-color: rgba(255, 255, 255, 0.9) !important;
            color: black !important;
        }
        [data-testid="stDataFrame"] {
            background: white;
            padding: 10px;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

add_bg_and_style()

 #--- LLM INITIALIZATION ---
@st.cache_resource
def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            api_key=api_key
        )
    return None

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --- AUTHENTICATION ---
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<div class='premium-card' style='text-align:center;'>", unsafe_allow_html=True)
        st.title("🏦 BankBot Portal")
        t1, t2 = st.tabs(["🔐 Login", "📝 create new account"])
        
        with t1:
            acc = st.text_input("Account Number", key="login_acc")
            pwd = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Access Account", use_container_width=True):
                user = get_account(acc)
                if user and verify_password(pwd, user[4]):
                    st.session_state.logged_in = True
                    st.session_state.user_name = user[1]
                    st.session_state.acc_no = acc
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        
        with t2:
            n_name = st.text_input("Full Name")
            n_acc = st.text_input("New Acc Number")
            n_bal = st.number_input("Initial Deposit", min_value=500)
            n_pwd = st.text_input("Set Password", type="password")
            if st.button("Create Account", use_container_width=True):
                create_account(n_name, n_acc, "Savings", n_bal, n_pwd)
                st.success("Registration Successful! Please log in.")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # --- SIDEBAR ---
    with st.sidebar:
        name = st.session_state.user_name.lower()
       # Logic: If name contains any female keywords -> female.png, else default to male.png
        if any(x in name for x in ['kavya', 'kusuma', 'bhoomi']):
            avatar = "assets/female.png"
        else:
         avatar = "assets/male.png"
        st.image(avatar if os.path.exists(avatar) else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.write(f"### {st.session_state.user_name}")
        menu = st.radio("Menu", ["Dashboard", "AI Chatbot", "History", "Safety & Schemes", "Help"])
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- PAGES ---
    if menu == "Dashboard":
        u = get_account(st.session_state.acc_no)
        st.markdown(f"""
            <div class="premium-card">
                <h3>Welcome back, {st.session_state.user_name}</h3>
                <p style="font-size: 1.2em; opacity: 0.8;">Account Balance</p>
                <h1 style="color: #00d4ff; font-size: 3em;">${u[3]:,.2f}</h1>
                <hr>
                <p>Status: <span style="color:#28a745;">● Active</span> | Account No: {u[0]}</p>
            </div>
            """, unsafe_allow_html=True)

                             
    elif menu == "AI Chatbot":
            st.title("🤖 Chat Assistant")

            # Initialize session state for tracking active forms and the current command
            if "active_form" not in st.session_state:
                st.session_state.active_form = None
            if "current_cmd" not in st.session_state:
                st.session_state.current_cmd = None

            # 1. Display Chat History
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            # 2. Get User Input
            prompt = st.chat_input("Check balance, Send money, block card, or ask a question...")
            
            if prompt:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                cmd = prompt.lower()
                st.session_state.current_cmd = cmd # Store the prompt to persist through form re-runs
                
                # Determine which form to show based on keywords
                if "balance" in cmd:
                    st.session_state.active_form = "balance"
                elif "send" in cmd or "transfer" in cmd:
                    st.session_state.active_form = "transfer"
                elif "block" in cmd:
                    st.session_state.active_form = "block"
                else:
                    st.session_state.active_form = "llm"

            # 3. Render the Assistant Response or Form based on active_form
            if st.session_state.active_form:
                with st.chat_message("assistant"):
                    
                    # --- CHECK BALANCE LOGIC ---
                    if st.session_state.active_form == "balance":
                        with st.form("bal_f"):
                            st.write("Please verify your identity to see balance.")
                            p = st.text_input("Verify Password", type="password")
                            if st.form_submit_button("Show Balance"):
                                u = get_account(st.session_state.acc_no)
                                if verify_password(p, u[4]):
                                    balance_msg = f"✅ Your current balance is: **${u[3]:,.2f}**"
                                    st.success(balance_msg)
                                    st.toast("Balance fetched!", icon="💰")
                                    st.session_state.chat_history.append({"role": "assistant", "content": balance_msg})
                                    st.session_state.active_form = None # Reset
                                else: 
                                    st.error("Incorrect Password. Please try again.")

                    # --- TRANSFER MONEY LOGIC ---
                    elif st.session_state.active_form == "transfer":
                        with st.form("tx_f"):
                            st.write("💸 Money Transfer")
                            to = st.text_input("Recipient Account Number")
                            amt = st.number_input("Amount ($)", min_value=1.0)
                            p = st.text_input("Enter Transaction Password", type="password")
                            submit = st.form_submit_button("Confirm Transfer")
                            
                            if submit:
                                res = transfer_money(st.session_state.acc_no, to, amt, p)
                                if "Successful" in res:
                                    st.balloons()
                                    st.success(f"🎉 {res}")
                                    st.toast("Transaction recorded in bankbot.db", icon="🚀")
                                    st.session_state.chat_history.append({"role": "assistant", "content": f"Transfer Successful: {res}"})
                                    st.session_state.active_form = None # Reset
                                else:
                                    # This handles the "Password not matching" error from your bank_crud.py
                                    st.error(f"❌ {res}")

                    # --- BLOCK CARD LOGIC ---
                    elif st.session_state.active_form == "block":
                        with st.form("block_f"):
                            st.warning("Are you sure you want to block your account?")
                            p = st.text_input("Enter Password to confirm", type="password")
                            if st.form_submit_button("BLOCK ACCOUNT NOW"):
                                u = get_account(st.session_state.acc_no)
                                if verify_password(p, u[4]):
                                    conn = get_conn()
                                    conn.execute("UPDATE accounts SET account_type='BLOCKED' WHERE account_number=?", (st.session_state.acc_no,))
                                    conn.commit()
                                    st.snow()
                                    block_msg = "🚫 ACCOUNT BLOCKED SUCCESSFULLY"
                                    st.error(block_msg)
                                    st.session_state.chat_history.append({"role": "assistant", "content": block_msg})
                                    st.session_state.active_form = None
                                else:
                                    st.error("Wrong password. Action cancelled.")

                    # --- GENERAL AI (LLM) LOGIC ---
                    elif st.session_state.active_form == "llm":
                        llm = get_llm()
                        if llm:
                            with st.spinner("Consulting AI Engine..."):
                                # Use the persistent command
                                response = llm.invoke([HumanMessage(content=st.session_state.current_cmd)])
                                st.write(response.content)
                                st.session_state.chat_history.append({"role": "assistant", "content": response.content})
                                st.session_state.active_form = None # Reset to allow new questions
                        else:
                            st.error("LLM not configured. Check your API Key.")
                

    # --- HISTORY PAGE ---



    elif menu == "History":
        st.title("📜 Transactions")
        conn = get_conn()
        # Querying the actual bankbot.db file
        df = pd.read_sql_query("SELECT timestamp, from_account, to_account, amount FROM transactions WHERE from_account=? OR to_account=? ORDER BY timestamp DESC", 
                               conn, params=(st.session_state.acc_no, st.session_state.acc_no))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent transactions found in bankbot.db")

    elif menu == "Safety & Schemes":
        st.title("🛡️ Bank Safety")
        st.markdown("<div class='premium-card'><ul><li><b>Scheme A:</b> 7% Interest</li><li><b>Safety:</b> Never share OTP</li></ul></div>", unsafe_allow_html=True)
        st.video("https://www.youtube.com/shorts/9g-vzZUfZEQ")

    elif menu == "Help":
        st.title("❓ Help & Support")
        st.write("📞 Support: 1-800-BANK-BOT")
        st.write("📺 [YouTube Tutorial: Secure Banking](https://www.youtube.com/shorts/nC81-uPY7ak)")
        


        
