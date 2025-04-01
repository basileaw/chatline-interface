from chatline import Interface

aws_config = {
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
}

chat = Interface(
    aws_config=aws_config,
)
chat.start()