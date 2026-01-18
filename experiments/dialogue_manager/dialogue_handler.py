from database.bank_crud import (
    get_account,
    transfer_money,
    list_accounts,
)

def handle(self, intent, entities, user_text):
    # Fix: Add safety check for NoneType
    if user_text is None:
        return "I'm sorry, I didn't receive any text. How can I help you?"
    
    user_text = user_text.strip()
    
    # Rest of your logic...
    if intent is None:
        # call your LLM logic here
        pass

class DialogueManager:
    def __init__(self):
        self.reset()

    def reset(self):
        self.active_intent = None
        self.slots = {}
        self.awaiting = None
        self.in_flow = False

    # =================================================
    # MAIN HANDLER
    # =================================================
    def handle(self, intent, entities, user_text):
        user_text = user_text.strip()

        # ---------- GLOBAL CANCEL ----------
        if user_text.lower() in ["cancel", "stop", "exit"]:
            self.reset()
            return "❌ Operation cancelled. How else can I help you?"

        # ---------- INTENT LOCK ----------
        if self.in_flow:
            intent = self.active_intent
        else:
            self.reset()
            self.active_intent = intent

            #----out of scop detection ----
        #     #checck original intent,not the locked one
        # if original_intent == "out_of_scope":
        #     self.reset()
        #     # `````````````````````````````````````````````````````````````````````````````````````````````````return "❓ Sorry, I can only assist with banking-related queries."

        # ---------- GREET ----------
        if intent == "greet":
            return "👋 Hello! How can I help you today?"

        # ---------- TRANSFER MONEY ----------
        if intent == "transfer_money":
            self.in_flow = True
            return self._handle_transfer(entities, user_text)

        # ---------- CHECK BALANCE ----------
        if intent == "check_balance":
            self.in_flow = True
            return self._handle_check_balance(entities, user_text)

        # ---------- CARD BLOCK ----------
        if intent == "card_block":
            return "🔒 Your card has been blocked successfully."

        return "❓ Sorry, I didn't understand. Please try again."

    # =================================================
    # TRANSFER MONEY FLOW
    # =================================================
    def handle_transfer(self, entities, user_text):

        # ---- Handle awaiting inputs ----
        if self.awaiting == "from_account":
            self.slots["from_account"] = user_text
            self.awaiting = None

        elif self.awaiting == "amount":
            try:
                self.slots["amount"] = float(user_text)
                self.awaiting = None
            except ValueError:
                return "❌ Please enter a valid amount."

        elif self.awaiting == "password":
            self.slots["password"] = user_text
            self.awaiting = None

            accounts = list_accounts()
            receivers = [
                f"{u} ({a})" for a, u in accounts
                if a != self.slots["from_account"]
            ]

            if not receivers:
                self.reset()
                return "❌ No receiver accounts available."

            self.awaiting = "receiver"
            return "➡️ Select receiver account:\n" + "\n".join(receivers)

        elif self.awaiting == "receiver":
            to_acc = user_text.split("(")[-1].replace(")", "").strip()

            result = transfer_money(
                self.slots["from_account"],
                to_acc,
                self.slots["amount"],
                self.slots["password"]
            )

            self.reset()
            return result

        # ---- Fill slots from entities ----
        for e in entities:
            if e["entity"] == "account_number" and "from_account" not in self.slots:
                self.slots["from_account"] = e["value"]

            elif e["entity"] == "amount" and "amount" not in self.slots:
                try:
                    self.slots["amount"] = float(e["value"])
                except ValueError:
                    pass

        # ---- Ask missing slots ----
        if "from_account" not in self.slots:
            self.awaiting = "from_account"
            return "🏦 Please provide your account number."

        acc = get_account(self.slots["from_account"])
        if not acc:
            self.awaiting = "from_account"
            self.slots.pop("from_account", None)
            return "❌ Invalid account number. Please re-enter."

        if "amount" not in self.slots:
            self.awaiting = "amount"
            return "💰 Please provide the amount to transfer."

        if "password" not in self.slots:
            self.awaiting = "password"
            return "🔐 Please provide your account password."

        return "⏳ Processing transfer..."

    # =================================================
    # CHECK BALANCE FLOW
    # =================================================
    def _handle_check_balance(self, entities, user_text):

        if self.awaiting == "account_number":
            acc_no = user_text.strip()
            acc = get_account(acc_no)

            if not acc:
                return "❌ Invalid account number. Please try again."

            _, name, acc_type, balance, _ = acc
            self.reset()
            return (
                f"👤 Account Holder: {name}\n"
                f"🏦 Account Type: {acc_type}\n"
                f"💰 Current Balance: ₹ {balance}"
            )

        # ---- Fill entity ----
        for e in entities:
            if e["entity"] == "account_number":
                self.slots["account_number"] = e["value"]

        if "account_number" not in self.slots:
            self.awaiting = "account_number"
            return "🏦 Please provide your account number to check balance."

        acc = get_account(self.slots["account_number"])
        if not acc:
            self.awaiting = "account_number"
            self.slots.pop("account_number", None)
            return "❌ Invalid account number. Please re-enter."

        _, name, acc_type, balance, _ = acc
        self.reset()

        return (
            f"👤 Account Holder: {name}\n"
            f"🏦 Account Type: {acc_type}\n"
            f"💰 Current Balance: ₹ {balance}"
        )


# from database.bank_crud import get_account, transfer_money

# class DialogueManager:

#     def handle(self, user_text, user_acc=None):
#         text = user_text.lower()

#         # CHECK BALANCE
#         if "balance" in text:
#             if not user_acc:
#                 return "❌ Please login first"
#             acc = get_account(user_acc)
#             return f"💰 Your balance is ₹{acc[3]}"

#         # SEND MONEY
#         if "send" in text or "transfer" in text:
#             words = text.split()
#             amount = None
#             to_acc = None

#             for w in words:
#                 if w.isdigit():
#                     if not amount:
#                         amount = int(w)
#                     else:
#                         to_acc = w

#             if not amount or not to_acc:
#                 return "❌ Format: send 500 to 9876543210"

#             return "🔐 Please use transfer option below"

#         return "🤖 I can help you with balance check or money transfer"

# # ;;;;;
# class DialogueManager:
#     def __init__(self):
#         pass

#     # --------------------------------------------------
#     # SIMPLE TEXT HANDLER (used in User Query & fallback)
#     # --------------------------------------------------
#     def handle(self, user_text):
#         text = user_text.lower()

#         if "balance" in text:
#             return "💰 To check balance, please provide your account number."

#         if "transfer" in text or "send money" in text:
#             return "💸 To transfer money, go to Database → Transfer Money section."

#         if "create" in text and "account" in text:
#             return "🏦 You can create an account from Database → Create Account."

#         if "hello" in text or "hi" in text:
#             return "👋 Hello! How can I assist you today?"

#         return "🤖 Sorry, I didn't understand that. Please try another query."

#     # --------------------------------------------------
#     # NLU BASED HANDLER (used when intent model exists)
#     # --------------------------------------------------
#     def process(self, intent_data):
#         """
#         intent_data example:
#         {
#             'intent': 'transfer_money',
#             'entities': {'amount': 500, 'to_account': '1234'},
#             'text': 'send 500 to 1234'
#         }
#         """

#         intent = intent_data.get("intent")
#         entities = intent_data.get("entities", {})
#         user_text = intent_data.get("text", "")

#         if intent == "check_balance":
#             return "💰 Please enter your account number to check balance."

#         if intent == "transfer_money":
#             return "💸 Please go to Database → Transfer Money to complete the transfer."

#         if intent == "create_account":
#             return "🏦 Please visit Database → Create Account."

#         return self.handle(user_text)
