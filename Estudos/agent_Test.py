
from agno.agent import Agent
from agno.models.groq import Groq

from Estudos.generator import criar_pbip


agente = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    tools=[criar_pbip],
    instructions=["Você cria projetos Power BI no formato .pbip"],
    show_tool_calls=True,
)

agente.print_response(
    "Crie um projeto chamado VendasBA na pasta C:/projetos "
    "usando o CSV C:/dados/vendas.csv"
)