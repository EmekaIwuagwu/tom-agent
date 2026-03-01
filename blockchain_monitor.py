import time
import requests
import logging
from memory import get_memory_instance
logger = logging.getLogger(__name__)

NETWORKS = {
    "KORTANA TESTNET": {
        "rpc_url": "https://poseidon-rpc.testnet.kortana.xyz/",
        "chain_id": 72511,
        "explorer": "https://explorer.testnet.kortana.xyz"
    },
    "KORTANA MAINNET": {
        "rpc_url": "https://zeus-rpc.mainnet.kortana.xyz",
        "chain_id": 7251,
        "explorer": "https://explorer.mainnet.kortana.xyz"
    }
}

def fetch_latest_block(rpc_url: str):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    try:
        response = requests.post(rpc_url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'result' in data:
            return int(data['result'], 16)
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching block from {rpc_url}: {e}")
        return None

def check_explorer(url: str):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error checking explorer {url}: {e}")
        return False

def check_networks(is_automated: bool = False):
    """
    Checks the status of both networks.
    If is_automated is True, it only sends a Telegram message if there's an issue or if it's the daily summary.
    If is_automated is False (on-demand), it always sends a message.
    """
    from telegram_bot import send_message_to_owner
    memory = get_memory_instance()
    
    testnet_block = fetch_latest_block(NETWORKS["KORTANA TESTNET"]["rpc_url"])
    mainnet_block = fetch_latest_block(NETWORKS["KORTANA MAINNET"]["rpc_url"])
    
    testnet_explorer_up = check_explorer(NETWORKS["KORTANA TESTNET"]["explorer"])
    mainnet_explorer_up = check_explorer(NETWORKS["KORTANA MAINNET"]["explorer"])

    current_timestamp = time.time()
    
    status_msg = "✅ All systems operational"
    issues = []
    
    if testnet_block is None:
        issues.append("Testnet RPC is unreachable.")
    if mainnet_block is None:
        issues.append("Mainnet RPC is unreachable.")
    if not testnet_explorer_up:
        issues.append("Testnet explorer is down.")
    if not mainnet_explorer_up:
        issues.append("Mainnet explorer is down.")
        
    last_status = None
    history = memory.data.get("network_status_history", [])
    if history:
        last_status = history[-1]
        
    # Check for stalls
    if last_status:
        time_diff = current_timestamp - last_status["timestamp"]
        if time_diff >= 300: # 5 minutes
            if testnet_block and last_status["testnet_block"] and testnet_block == last_status["testnet_block"]:
                issues.append(f"Testnet is stalled at block {testnet_block} for {(time_diff/60):.1f} mins.")
            if mainnet_block and last_status["mainnet_block"] and mainnet_block == last_status["mainnet_block"]:
                issues.append(f"Mainnet is stalled at block {mainnet_block} for {(time_diff/60):.1f} mins.")

    if issues:
        status_msg = "❌ ISSUES DETECTED:\n- " + "\n- ".join(issues)
        
    # Save current status
    memory.add_network_status({
        "timestamp": current_timestamp,
        "testnet_block": testnet_block,
        "mainnet_block": mainnet_block,
        "status": status_msg
    })
    
    report = (
        f"📊 *Network Status Report*\n\n"
        f"KORTANA TESTNET:\n"
        f"• Block: `{testnet_block}`\n"
        f"• Explorer: {'🟢 UP' if testnet_explorer_up else '🔴 DOWN'}\n\n"
        f"KORTANA MAINNET:\n"
        f"• Block: `{mainnet_block}`\n"
        f"• Explorer: {'🟢 UP' if mainnet_explorer_up else '🔴 DOWN'}\n\n"
        f"STATUS: {status_msg}"
    )

    if not is_automated or issues:
        send_message_to_owner(report)
        
    return report
