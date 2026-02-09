import unittest
from pathlib import Path
import shutil
import json

from src.services.task_generator import TaskGenerator

class TestTaskGenerator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for Needs_Action
        self.temp_dir = Path('temp_needs_action')
        self.temp_dir.mkdir(exist_ok=True)
        # Override settings for the test
        from src.config import settings
        self.original_path = settings.NEEDS_ACTION_PATH
        settings.NEEDS_ACTION_PATH = str(self.temp_dir)
        self.generator = TaskGenerator()
        # Create a sample source file
        self.sample_file = Path('sample.txt')
        self.sample_file.write_text('Hello world')

    def tearDown(self):
        # Restore original setting
        from src.config import settings
        settings.NEEDS_ACTION_PATH = self.original_path
        # Clean up temporary files
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.sample_file.exists():
            self.sample_file.unlink()

    def test_create_task_creates_file(self):
        task_path = self.generator.create_task(self.sample_file)
        self.assertIsNotNone(task_path)
        self.assertTrue(task_path.exists())
        data = json.loads(task_path.read_text())
        self.assertEqual(data['source_path'], str(self.sample_file))
        self.assertIn('file_hash', data)
        self.assertEqual(data['status'], 'pending')

    def test_duplicate_detection(self):
        # First creation
        first_task = self.generator.create_task(self.sample_file)
        self.assertIsNotNone(first_task)
        # Second creation should return None (duplicate)
        second_task = self.generator.create_task(self.sample_file)
        self.assertIsNone(second_task)

if __name__ == '__main__':
    unittest.main()
