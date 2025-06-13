from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv
load_dotenv()
from crewai.project import CrewBase, agent, crew, task
from project.tools.db_tools import (
    DetectDatabaseTool,
    GenerateSecureCredentialsTool,
    CreateLocalDBUserTool,
    InjectCredentialsTool,
    CreateLocalDBUserFromContextTool,
    InjectCredentialsFromContextTool
)
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators
@CrewBase
class Project():
    """Project crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools

    @agent
    def db_inspector(self) -> Agent:
        return Agent(
            config=self.agents_config['db_inspector'], # type: ignore[index]
            tools=[
            DetectDatabaseTool(),
            GenerateSecureCredentialsTool(),
            CreateLocalDBUserTool(),
            InjectCredentialsTool(),
            CreateLocalDBUserFromContextTool(),
            InjectCredentialsFromContextTool()
        ],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def detect_database(self) -> Task:
        return Task(
            config=self.tasks_config['detect_database'], # type: ignore[index]
        )
    @task
    def generate_credentials(self) -> Task:
        return Task(
            config=self.tasks_config['generate_credentials'],
            context=[self.detect_database()]
        )
    @task
    def create_db_user(self) -> Task:
        return Task(
            config=self.tasks_config['create_db_user'],
            context=[self.detect_database(), self.generate_credentials()]
        )
    @task
    def inject_credentials(self) -> Task:
        return Task(
            config=self.tasks_config['inject_credentials'],
            context=[self.detect_database(), self.generate_credentials(), self.create_db_user()]
        )
    @crew
    def crew(self) -> Crew:
        """Creates the Project crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
