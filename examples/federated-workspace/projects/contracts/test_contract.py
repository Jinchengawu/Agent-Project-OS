import json
from pathlib import Path
import unittest


class ContractTest(unittest.TestCase):
    def test_contract_declares_required_fields(self):
        schema = json.loads((Path(__file__).parent / "contracts" / "order.schema.json").read_text())
        self.assertEqual(schema["required"], ["order_id", "total_minor"])


if __name__ == "__main__":
    unittest.main()
