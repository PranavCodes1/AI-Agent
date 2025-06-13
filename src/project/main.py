#!/usr/bin/env python
import sys
import warnings
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

from project.crew import Project

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    inputs = {
        'project_path': '/home/pranav/imcc-project/AI-Agent/sample_project_mysql',
        'current_year': str(datetime.now().year)
    }
    
    try:
        result = Project().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    if len(sys.argv) < 3:
        print("Usage: train <n_iterations> <filename>")
        sys.exit(1)
        
    inputs = {
        "project_path": "/home/pranav/imcc-project/AI-Agent/sample_project_mysql",
        'current_year': str(datetime.now().year)
    }
    try:
        Project().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    if len(sys.argv) < 2:
        print("Usage: replay <task_id>")
        sys.exit(1)
        
    try:
        Project().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    if len(sys.argv) < 3:
        print("Usage: test <n_iterations> <eval_llm>")
        sys.exit(1)
        
    inputs = {
        "project_path": "/home/pranav/imcc-project/AI-Agent/sample_project_mysql",
        "current_year": str(datetime.now().year)
    }
    
    try:
        Project().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == "__main__":
    run()
