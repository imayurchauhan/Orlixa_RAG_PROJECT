import app.llm as llm


def run_tests():
    question_guidance = llm._build_question_guidance(
        "is there a diff paragraphs? yes or no?",
    )
    assert "compare the text content directly" in question_guidance
    assert "start the answer with exactly 'Yes.' or 'No.'" in question_guidance

    detailed_prompt = llm._build_multimodal_system_message(
        "general",
        "please describe this image in very detail point wise",
    )
    assert "Use the chat history carefully" in detailed_prompt
    assert "The user wants a long, detailed answer." in detailed_prompt
    assert "point-wise description" in detailed_prompt
    assert "foreground" in detailed_prompt
    assert "background" in detailed_prompt

    comparison_prompt = llm._build_multimodal_system_message(
        "general",
        "can you compare two paragraphs and check this description is of same picture or not? yes or no?",
    )
    assert "prioritize comparing the text provided" in comparison_prompt
    assert "start with exactly 'Yes.' or 'No.'" in comparison_prompt
    assert "start with a clear verdict" in comparison_prompt
    assert "compare point by point" in comparison_prompt
    assert "which details match" in comparison_prompt

    user_text = llm._build_multimodal_user_text(
        "Does this description match the image?",
        "Chat History:\nAssistant: The image shows children in a park.\n\n",
        "A short context block.",
    )
    assert "--- CHAT HISTORY ---" in user_text
    assert "--- TEXT CONTEXT ---" in user_text
    assert "--- USER QUESTION ---" in user_text
    assert "Does this description match the image?" in user_text

    print("LLM PROMPT GUIDANCE TESTS PASSED")


if __name__ == "__main__":
    run_tests()
