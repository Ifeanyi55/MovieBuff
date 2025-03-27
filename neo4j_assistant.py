from CyVer.validators import SyntaxValidator,PropertiesValidator
from fastrtc import (ReplyOnPause,Stream,get_stt_model,get_tts_model)
from neo4j import GraphDatabase,basic_auth
from dotenv import load_dotenv
from mistralai import Mistral
import json
import os

load_dotenv()

def neo4jVoice(audio):
  model = "mistral-large-latest"

  api_key = os.getenv("MISTRAL_API_KEY")

  client = Mistral(api_key)

  # neo4j movie sandbox login credentials
  database_url = "bolt://54.90.87.77:7687"
  database_username = "neo4j"
  database_password = "trigger-shoe-hub"

  driver = GraphDatabase.driver(database_url, auth=basic_auth(database_username, database_password))

  stt_model = get_stt_model()
  tts_model = get_tts_model()   

  prompt = stt_model.stt(audio)

  few_shot_examples = [
    {
        "question": "Who acted in the movie 'The Matrix'?",
        "cypher": "MATCH (actor:Person)-[:ACTED_IN]->(movie:Movie {title: 'The Matrix'}) RETURN actor.name"
    },
    {
        "question": "What movies did Christopher Nolan direct?",
        "cypher": "MATCH (director:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(movie:Movie) RETURN movie.title"
    },
    {
        "question": "Who wrote the screenplay for 'Pulp Fiction'?",
        "cypher": "MATCH (writer:Person)-[:WROTE]->(movie:Movie {title: 'Pulp Fiction'}) RETURN writer.name"
    },
    {
        "question": "In what year was 'The Matrix' released?",
        "cypher": "MATCH (movie:Movie{title:'The Matrix'}) RETURN movie.released As Released"
    },
    {
        "question": "Can you tell me what year 'The Matrix' was released?",
        "cypher": "MATCH (movie:Movie{title:'The Matrix'}) RETURN movie.released As Released"
    },
    {
        "question": "In what year was Tom Hanks born?",
        "cypher": "MATCH (actor:Person{name:'Tom Hanks'}) RETURN actor.born As Born"
    },
    {
        "question": "Can you tell me in what year Jack Nicholson was born?",
        "cypher": "MATCH (actor:Person{name:'Jack Nicholson'}) RETURN actor.born As Born"
    },
    {
        "question": "In what year was Jack Nicholson born?",
        "cypher": "MATCH (actor:Person{name:'Jack Nicholson'}) RETURN actor.born As Born"
    },
    {
        "question": "What is the tagline of 'The Matrix'?",
        "cypher": "MATCH (movie:Movie{title:'The Matrix'}) RETURN movie.tagline As Tagline"
    },
    {
        "question": "What is the tagline of 'Forrest Gump'?",
        "cypher": "MATCH (movie:Movie{title:'Forrest Gump'}) RETURN movie.tagline As Tagline"
    },
    {
        "question": "Which movies did Tom Cruise act in?",
        "cypher": "MATCH (actor:Person{name:'Tom Cruise'})-[:ACTED_IN]->(movie:Movie) RETURN movie.title As Movies"
    },
    {
        "question": "Which movies did Cuba Gooding Jr act in?",
        "cypher": "MATCH (actor:Person{name:'Cuba Gooding Jr'})-[:ACTED_IN]->(movie:Movie) RETURN movie.title As Movies"
    }
  ]

  # Create a structured prompt with few-shot examples
  few_shot_prompt = "I want you to convert natural language questions about movies into valid Neo4j Cypher statements. Return the response as a JSON object with a fixed key structure containing only the key 'cypher' with the Cypher query as its value.\n\nExamples:\n"

  for example in few_shot_examples:
      few_shot_prompt += f"Question: {example['question']}\nCypher: {example['cypher']}\nResult: {{'cypher': '{example['cypher']}'}}\n\n"

      few_shot_prompt += f"Question: {prompt}\nCypher:"

  chat_response = client.chat.complete(
      model=model,
      messages=[
          {
              "role": "user",
              "content": few_shot_prompt
          }
      ],
      response_format={"type": "json_object"}
  )

  movie_cypher = chat_response.choices[0].message.content

  movie_cypher = json.loads(movie_cypher)

  movie_cypher = movie_cypher['cypher']

  # check validity of generated cypher statement
  driver = GraphDatabase.driver(database_url, auth=basic_auth(database_username, database_password))
  
  # properties_validator = PropertiesValidator(driver)
  syntax_validator =  SyntaxValidator(driver)

  # is_valid_prop = properties_validator.validate(movie_cypher)
  is_valid_syntax = syntax_validator.validate(movie_cypher)

  if is_valid_syntax:

    # query neo4j database
    query_resp = driver.session().run(movie_cypher).data()

    if isinstance(query_resp,list) and len(query_resp) == 0:

      query_resp = "No result found"

    else:

      resp_message = client.chat.complete(
      model=model,
      messages=[
          {
              "role": "user",
              "content": f"I want you to convert this {query_resp} into a natural language response. Use the {prompt} to guide your response."
          }
        ]
      )

      bot_resp = resp_message.choices[0].message.content

      for audio_chunk in tts_model.stream_tts_sync(bot_resp):
        yield audio_chunk


  else:
        
    response = "I'm sorry, but I am unable to give you the information you require at this time."

    for audio_chunk in tts_model.stream_tts_sync(response):
      yield audio_chunk

if __name__ == "__main__":
    stream = Stream(ReplyOnPause(neo4jVoice), modality="audio", mode="send-receive")
    stream.ui.launch()
