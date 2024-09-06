import streamlit as st
import asyncio
from typing import List, Tuple
from models import TeacherAgentOutput, QuizMakerOutput
from agents_korean import process_sentence, quiz_maker_agent
from config import OUTPUT_FILE

# Configure logging for Streamlit

# Asynchronous function to process all sentences and generate quiz concurrently
async def process_all_sentences_and_generate_quiz(sentences: List[str]) -> Tuple[List[TeacherAgentOutput], QuizMakerOutput]:
    # Process all sentences concurrently
    sentence_tasks = [process_sentence(sentence) for sentence in sentences]
    results = await asyncio.gather(*sentence_tasks)
    
    print("\n\n\n\n\n RESULTS ARE HERE:\n", results)

    # Generate quiz based on the results
    quiz_output = await quiz_maker_agent(results)
    
    return results, quiz_output

# Synchronous wrapper for the entire process
def sync_process_and_quiz(sentences: List[str]) -> Tuple[List[TeacherAgentOutput], QuizMakerOutput]:
    return asyncio.run(process_all_sentences_and_generate_quiz(sentences))

# Initialize session state
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'quiz_questions' not in st.session_state:
    st.session_state['quiz_questions'] = []
if 'quiz_submitted' not in st.session_state:
    st.session_state['quiz_submitted'] = False
if 'user_answers' not in st.session_state:
    st.session_state['user_answers'] = {}
 
# Main app layout
st.set_page_config(page_title="English Language Analyzer & Quiz", layout="wide")

st.title("🇰🇷 Grammar Assistant")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Input", "Analysis", "Quiz"])

with tab1:
    st.header("Enter Your Sentences")
    sentences = st.text_area("Type or paste your sentences here (separate multiple sentences with a newline):", height=200)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        submit_button = st.button("Analyze and Generate Quiz", use_container_width=True)

    if submit_button:
        input_sentences = [s.strip() for s in sentences.split("\n") if s.strip()]
        if input_sentences:
            with st.spinner("Analyzing sentences and generating quiz..."):
                results, quiz_output = sync_process_and_quiz(input_sentences)
                st.session_state['results'] = results
                st.session_state['quiz_questions'] = quiz_output.questions
                st.session_state['quiz_submitted'] = False
                st.session_state['user_answers'] = {}
            st.success("Analysis complete and quiz generated! Check the 'Analysis' and 'Quiz' tabs.")

with tab2:
    st.header("Analysis Results")
    if st.session_state['results']:
        for i, result in enumerate(st.session_state['results'], 1):
            icon = "✅" if result.original_sentence == result.correct_sentence else "❌"
            with st.expander(f"{icon} {result.original_sentence}"):
                if result.original_sentence != result.correct_sentence:
                    st.markdown(f"**Corrected Sentence:** {result.correct_sentence}")
                st.markdown(f"**Explanation:** {result.explanation}")
    else:
        st.info("No results to display. Go to the 'Input' tab to analyze sentences.")

with tab3:
    st.header("Quiz")
    if st.session_state['quiz_questions']:
        for i, question in enumerate(st.session_state['quiz_questions'], 1):
            choice = st.radio(f"**Q{i}. {question.question}**", question.choices, key=f"question_{i}", index=None)
            st.session_state['user_answers'][i] = choice

        if st.button("Submit Quiz"):
            # Check if all questions have been answered
            unanswered_questions = [i for i, ans in st.session_state['user_answers'].items() if ans is None]
            
            if unanswered_questions:
                st.error(f"Please answer all questions before submitting. Unanswered questions: {', '.join(map(str, unanswered_questions))}")
            else:
                st.session_state['quiz_submitted'] = True

        if st.session_state.get('quiz_submitted', False):
            st.markdown("## Quiz Results")
            score = 0
            for i, question in enumerate(st.session_state['quiz_questions'], 1):
                st.markdown(f"<h5>Q{i}. {question.question}</h5>", unsafe_allow_html=True)
                
                user_answer = st.session_state['user_answers'].get(i, '')
                is_correct = user_answer.startswith(question.answer)
                
                # Display choices with correct and user answers highlighted
                for choice in question.choices:
                    if choice.startswith(question.answer):
                        st.markdown(f"✅ **{choice}** (Correct Answer)")
                    elif choice == user_answer:
                        st.markdown(f"❌ *{choice}* (Your Answer)")
                    else:
                        st.markdown(f"  {choice}")
                
                if is_correct:
                    st.success("Your answer is correct!")
                    score += 1
                
                st.markdown(f"**Explanation:** {question.explanation}")
                st.markdown("---")

            st.markdown(f"**Your final score: {score}/{len(st.session_state['quiz_questions'])}**")
    else:
        st.info("No quiz available. Analyze some sentences in the 'Input' tab first.")

