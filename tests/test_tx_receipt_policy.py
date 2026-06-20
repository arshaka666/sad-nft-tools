import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "hermes-crypto-agent" / "scripts"


def read(name: str) -> str:
    return (SCRIPTS / name).read_text()


class TxReceiptPolicyTests(unittest.TestCase):
    def test_auto_mint_hammer_uses_correct_mint_uint256_selector(self):
        source = read("auto_mint_hammer.py")
        self.assertIn('{"name": "mint(uint256)", "data": "0xa0712d68" + q', source)
        self.assertNotIn('{"name": "mint(uint256)", "data": "0x1249c58b" + q', source)
        self.assertIn('{"name": "mint()", "data": "0x1249c58b"', source)

    def test_evm_tx_engines_do_not_report_broadcast_as_final_success(self):
        for filename in ["contract_writer.py", "swap_engine.py", "nft_engine.py", "deploy_engine.py"]:
            source = read(filename)
            with self.subTest(filename=filename):
                self.assertIsNone(re.search(r"status\s*=\s*['\"]sent['\"]", source), filename)
                self.assertNotIn('WriteResult("sent"', source)
                self.assertNotIn('SwapResult(status="sent"', source)
                self.assertNotIn('NFTResult(status="sent"', source)
                self.assertNotIn('DeployResult("sent"', source)

    def test_engines_check_receipt_status_before_confirmed_success(self):
        expectations = {
            "contract_writer.py": ['wait_for_transaction_receipt', 'receipt.get("status") != 1', 'WriteResult("confirmed"'],
            "swap_engine.py": ['wait_for_transaction_receipt', 'receipt.get("status") != 1', 'SwapResult(status="confirmed"'],
            "nft_engine.py": ['wait_for_transaction_receipt', 'receipt.get("status") != 1', 'NFTResult(status="confirmed"'],
            "deploy_engine.py": ['wait_for_transaction_receipt', 'receipt.get("status") != 1', 'DeployResult("deployed"'],
        }
        for filename, needles in expectations.items():
            source = read(filename)
            for needle in needles:
                with self.subTest(filename=filename, needle=needle):
                    self.assertIn(needle, source)

    def test_bridge_engine_uses_source_receipt_and_pending_or_tracked_bridge_status(self):
        source = read("bridge_engine.py")
        self.assertIsNone(re.search(r"BridgeResult\(status\s*=\s*['\"]sent['\"]", source))
        self.assertIn('status="sent_pending_bridge"', source)
        self.assertIn('wait_for_transaction_receipt', source)
        self.assertIn('receipt.get("status") != 1', source)
        self.assertIn('lifi_track(', source)
        self.assertIn('layerzero_track(', source)


if __name__ == "__main__":
    unittest.main()
