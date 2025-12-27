import unittest
from src.shared.models import Runbook
from src.planner.loader import find_matching_runbook

class TestRunbookLoading(unittest.TestCase):
    def test_find_matching_runbook(self):
        # Should find the high_cpu runbook
        rb = find_matching_runbook("ec2-high-cpu-prod", "AWS/EC2")
        self.assertIsNotNone(rb)
        self.assertEqual(rb.runbook_id, "high_cpu_ec2_mitigate")

    def test_no_match(self):
        rb = find_matching_runbook("random-alarm", "AWS/RDS")
        self.assertIsNone(rb)

if __name__ == '__main__':
    unittest.main()
