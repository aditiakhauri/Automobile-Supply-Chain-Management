import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from web3 import Web3


load_dotenv()


app = Flask(__name__)


WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ISO_CID = os.getenv("ISO_CID")  
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))


with open("abi/AutomobileSupplyChain.json", "r") as abi_file:
    abi_data = json.load(abi_file)
    contract_abi = abi_data if isinstance(abi_data, list) else abi_data.get("abi")

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

account = w3.eth.account.from_key(PRIVATE_KEY)


@app.route("/")
def home():
    return "<h2>Automated Supply Payment Backend is Running</h2>"


@app.route("/createOrder", methods=["POST"])
def create_order():
    """
    POST /createOrder
    JSON Body: {
      "supplier": "0xCF10217bf58d9690f4857134eF745048Ad833b6E",
      "amount": 1.0,  # in ETH
      "vin": "VIN123456",
    }
    """
    data = request.get_json()
    supplier = data.get("supplier")
    amount_eth = data.get("amount")
    vin = data.get("vin")

    if not supplier or not amount_eth or not vin:
        return jsonify({"error": "Missing required fields"}), 400

    amount_wei = w3.to_wei(amount_eth, "ether")

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.createOrder(
            supplier, amount_wei, vin, f"ipfs://{ISO_CID}"
        ).build_transaction({
            "chainId": w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return jsonify({"status": "success", "txHash": tx_hash.hex()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/depositFunds", methods=["POST"])
def deposit_funds():
    """
    POST /depositFunds
    JSON Body: {
      "orderId": 1,
      "amount": 1.0  # in ETH
    }
    """
    data = request.get_json()
    order_id = data.get("orderId")
    amount_eth = data.get("amount")

    if not order_id or not amount_eth:
        return jsonify({"error": "Missing required fields"}), 400

    amount_wei = w3.to_wei("0.5", "ether")

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        gas_estimate = contract.functions.depositFunds(order_id).estimate_gas({
            "from": account.address,
            "value": amount_wei
        })
        tx = contract.functions.depositFunds(order_id).build_transaction({
            "chainId": w3.eth.chain_id,
            "gas": gas_estimate,
            "gasPrice": w3.to_wei("5", "gwei"),
            "nonce": nonce,
            "value": amount_wei
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return jsonify({"status": "success", "txHash": tx_hash.hex()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/markShipped", methods=["POST"])
def mark_shipped():
    """
    POST /markShipped
    JSON Body: {
      "orderId": 1
    }
    """
    data = request.get_json()
    order_id = data.get("orderId")

    if not order_id:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.markShipped(order_id).build_transaction({
            "chainId": w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return jsonify({"status": "success", "txHash": tx_hash.hex()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/confirmDelivery", methods=["POST"])
def confirm_delivery():
    """
    POST /confirmDelivery
    JSON Body: {
      "orderId": 1
    }
    """
    data = request.get_json()
    order_id = data.get("orderId")

    if not order_id:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.confirmDelivery(order_id).build_transaction({
            "chainId": w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return jsonify({"status": "success", "txHash": tx_hash.hex()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/getOrder/<int:order_id>", methods=["GET"])
def get_order(order_id):
    """
    GET /getOrder/<order_id>
    Returns details of the order
    """
    try:
        order = contract.functions.orders(order_id).call()
        return jsonify({
            "orderId": order[0],
            "buyer": order[1],
            "supplier": order[2],
            "amount": w3.fromWei(order[3], "ether"),
            "state": order[4],
            "vin": order[5],
            "isoTs16949Doc": order[6]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
