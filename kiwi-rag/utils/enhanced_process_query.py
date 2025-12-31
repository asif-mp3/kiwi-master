"""
Enhanced process_query function with context memory.
This replaces the existing process_query in streamlit_app.py
"""

def process_query(question: str):
    """Process a user query through the full RAG pipeline with context memory."""
    try:
        # Step 0: Check question cache for similar questions
        cache_result = st.session_state.question_cache.find_similar(question)
        
        if cache_result:
            answer, metadata, similarity = cache_result
            return {
                'success': True,
                'explanation': answer,
                'data': metadata.get('data'),
                'plan': metadata.get('plan'),
                'schema_context': metadata.get('schema_context'),
                'data_refreshed': False,
                'from_cache': True,
                'similarity': similarity
            }
        
        # Step 0.5: Check if follow-up question and resolve context
        original_question = question
        is_followup = st.session_state.context_resolver.is_followup(
            question, 
            st.session_state.messages
        )
        
        if is_followup:
            resolved_question = st.session_state.context_resolver.resolve_context(
                question,
                st.session_state.messages
            )
            question = resolved_question  # Use resolved question for processing
        
        # Automatic change detection before processing
        data_refreshed = check_and_refresh_data()
        
        # Step 1: Schema retrieval
        schema_context = retrieve_schema(question)
        
        # Step 2: Planning
        plan = generate_plan(question, schema_context)
        validate_plan(plan)
        
        # Step 3: Execution
        result = execute_plan(plan)
        
        # Step 4: Explanation
        explanation = explain_results(result, query_plan=plan, original_question=question)
        
        # Cache the result for future similar questions
        st.session_state.question_cache.add_to_cache(
            original_question,  # Cache with original question
            explanation,
            {
                'plan': plan,
                'data': result.to_dict() if hasattr(result, 'to_dict') else None,
                'schema_context': schema_context,
                'data_refreshed': data_refreshed
            }
        )
        
        return {
            'success': True,
            'explanation': explanation,
            'data': result,
            'plan': plan,
            'schema_context': schema_context,
            'data_refreshed': data_refreshed,
            'from_cache': False,
            'was_followup': is_followup,
            'resolved_question': question if is_followup else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'exception': e,
            'from_cache': False
        }
