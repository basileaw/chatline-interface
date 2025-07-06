# test_consecutive_rewind.py

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chatline.conversation.actions import ConversationActions
from chatline.conversation.history import ConversationHistory, ConversationState
from chatline.conversation.messages import ConversationMessages


class MockDisplay:
    def __init__(self):
        self.terminal = Mock()
        self.terminal.width = 80
        self.terminal.height = 24
        self.terminal.format_prompt = lambda msg: f"> {msg}"
        self.style = Mock()
        self.style.set_output_color = Mock()
        self.animations = Mock()
        
        # Mock reverse streamer
        self.reverse_streamer_mock = AsyncMock()
        self.animations.create_reverse_streamer.return_value = self.reverse_streamer_mock
        
        # Mock dot loader
        self.dot_loader_mock = AsyncMock()
        async def mock_run_with_loading(coro):
            return await coro
        self.dot_loader_mock.run_with_loading = mock_run_with_loading
        self.animations.create_dot_loader.return_value = self.dot_loader_mock


class MockStream:
    def __init__(self):
        self.generator = AsyncMock()
        
    def get_generator(self):
        return self.generator


class MockLogger:
    def __init__(self):
        self.debug = Mock()
        self.info = Mock()
        self.warning = Mock()
        self.error = Mock()
        

class TestConsecutiveRewind:
    """Test suite for consecutive rewind functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.display = MockDisplay()
        self.stream = MockStream()
        self.history = ConversationHistory()
        self.messages = ConversationMessages()
        self.preface = Mock()
        self.preface.styled_content = ""
        self.preface.clear = Mock()
        self.logger = MockLogger()
        
        # Mock the generator to return predictable responses
        async def mock_generator(*args, **kwargs):
            return ("assistant response", "styled response")
        
        self.stream.generator = mock_generator
        
        self.actions = ConversationActions(
            display=self.display,
            stream=self.stream,
            history=self.history,
            messages=self.messages,
            preface=self.preface,
            logger=self.logger
        )

    async def create_conversation_history(self, user_messages: List[str]) -> str:
        """
        Create a conversation history with the given user messages and responses.
        Returns the intro_styled content for rewind operations.
        """
        # Add system message and create initial state
        self.messages.add_message("system", "You are a helpful assistant.", 0)
        sys_prompt = self.actions._get_system_prompt()
        initial_state_msgs = await self.messages.get_messages(sys_prompt)
        self.history.update_state(messages=initial_state_msgs)
        self.actions.history_index = self.history.get_latest_state_index()
        
        # Process each user message to build conversation history
        for i, user_msg in enumerate(user_messages, 1):
            self.actions.current_turn = i
            
            # Add user message
            self.messages.add_message("user", user_msg, i)
            sys_prompt = self.actions._get_system_prompt()
            state_msgs = await self.messages.get_messages(sys_prompt)
            self.history.update_state(messages=state_msgs)
            self.actions.history_index = self.history.get_latest_state_index()
            
            # Add assistant response
            assistant_response = f"Response to: {user_msg}"
            self.messages.add_message("assistant", assistant_response, i)
            new_state_msgs = await self.messages.get_messages(sys_prompt)
            self.history.update_state(messages=new_state_msgs)
            self.actions.history_index = self.history.get_latest_state_index()
        
        # Create mock intro_styled content
        intro_styled = "Mock conversation display"
        return intro_styled

    @pytest.mark.asyncio
    async def test_single_rewind_basic(self):
        """Test basic single rewind functionality."""
        user_messages = ["first message", "second message", "third message"]
        intro_styled = await self.create_conversation_history(user_messages)
        
        # Perform rewind
        raw, styled, prompt = await self.actions.rewind_conversation(intro_styled)
        
        # Verify rewind worked
        assert raw == "assistant response"
        assert prompt == "> second message"
        
        # Check that messages state is correct
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs == ["first message", "second message"]

    @pytest.mark.asyncio
    async def test_consecutive_rewind_two_steps(self):
        """Test two consecutive rewind operations."""
        user_messages = ["msg1", "msg2", "msg3"]
        intro_styled = await self.create_conversation_history(user_messages)
        
        # First rewind: should go back to msg2
        raw1, styled1, prompt1 = await self.actions.rewind_conversation(intro_styled)
        assert prompt1 == "> msg2"
        
        # Update intro_styled to simulate what would happen in real usage
        intro_styled = "Updated conversation display after first rewind"
        
        # Second rewind: should go back to msg1
        raw2, styled2, prompt2 = await self.actions.rewind_conversation(intro_styled)
        
        assert prompt2 == "> msg1"
        
        # Verify final state
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs == ["msg1"]

    @pytest.mark.asyncio 
    async def test_consecutive_rewind_three_steps(self):
        """Test three consecutive rewind operations."""
        user_messages = ["alpha", "beta", "gamma", "delta"]
        intro_styled = await self.create_conversation_history(user_messages)
        
        # First rewind: delta -> gamma
        await self.actions.rewind_conversation(intro_styled)
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs[-1] == "gamma"
        
        # Second rewind: gamma -> beta  
        await self.actions.rewind_conversation(intro_styled)
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs[-1] == "beta"
        
        # Third rewind: beta -> alpha
        await self.actions.rewind_conversation(intro_styled)
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs[-1] == "alpha"

    @pytest.mark.asyncio
    async def test_rewind_after_new_response(self):
        """Test rewind after generating new response (simulating real usage pattern)."""
        user_messages = ["start", "middle", "end"]
        intro_styled = await self.create_conversation_history(user_messages)
        
        # First rewind
        await self.actions.rewind_conversation(intro_styled)
        
        # Simulate new response generation (what happens after rewind in real usage)
        new_response = "new response to middle"
        self.actions.messages.add_message("assistant", new_response, self.actions.current_turn)
        sys_prompt = self.actions._get_system_prompt()
        new_state_msgs = await self.messages.get_messages(sys_prompt)
        self.history.update_state(messages=new_state_msgs)
        self.actions.history_index = self.history.get_latest_state_index()
        
        # Second rewind should work correctly
        raw, styled, prompt = await self.actions.rewind_conversation(intro_styled)
        assert prompt == "> start"
        
        # Verify state
        user_msgs = [m.content for m in self.actions.messages.messages if m.role == "user"]
        assert user_msgs == ["start"]

    @pytest.mark.asyncio
    async def test_rewind_insufficient_history(self):
        """Test rewind behavior with insufficient conversation history."""
        # Only one user message
        user_messages = ["only message"]
        intro_styled = await self.create_conversation_history(user_messages)
        
        # Rewind should fail gracefully
        raw, styled, prompt = await self.actions.rewind_conversation(intro_styled)
        assert raw == ""
        assert styled == intro_styled
        assert prompt == ""

    @pytest.mark.asyncio
    async def test_rewind_empty_conversation(self):
        """Test rewind behavior with empty conversation."""
        intro_styled = "empty conversation"
        
        # Rewind should fail gracefully
        raw, styled, prompt = await self.actions.rewind_conversation(intro_styled)
        assert raw == ""
        assert styled == intro_styled
        assert prompt == ""

    def test_find_target_user_message(self):
        """Test the find_target_user_message helper method."""
        # Setup messages
        self.messages.add_message("system", "System prompt", 0)
        self.messages.add_message("user", "first", 1)
        self.messages.add_message("assistant", "response1", 1)
        self.messages.add_message("user", "second", 2)
        self.messages.add_message("assistant", "response2", 2)
        self.messages.add_message("user", "third", 3)
        
        # Should return second-to-last user message
        target = self.actions.find_target_user_message()
        assert target == "second"
        
    def test_find_target_user_message_insufficient_history(self):
        """Test find_target_user_message with insufficient history."""
        # Only one user message
        self.messages.add_message("user", "only", 1)
        
        target = self.actions.find_target_user_message()
        assert target is None

    @pytest.mark.asyncio
    async def test_find_state_before_user_message(self):
        """Test the find_state_before_user_message helper method."""
        user_messages = ["first", "second", "third"]
        await self.create_conversation_history(user_messages)
        
        # Find state before "second" message (should contain only "first")
        result = self.actions.find_state_before_user_message("second")
        assert result is not None
        
        state_index, state_data = result
        assert isinstance(state_index, int)
        assert isinstance(state_data, dict)
        
        # Verify the state contains the right messages (everything before "second")
        messages = state_data["messages"]
        user_msgs = [msg["content"] for msg in messages if msg["role"] == "user"]
        assert "first" in user_msgs  # Should contain messages before "second"
        assert "second" not in user_msgs  # Should NOT contain "second" (we want state before it)
        assert "third" not in user_msgs  # Should NOT contain "third"

    def test_validate_history_index(self):
        """Test history index validation."""
        # Valid index
        self.actions.history_index = 0
        self.history.state_history = [{"messages": []}]
        assert self.actions.validate_history_index() == True
        
        # Invalid index (too high)
        self.actions.history_index = 5
        assert self.actions.validate_history_index() == False
        
        # Invalid index (too low)
        self.actions.history_index = -2
        assert self.actions.validate_history_index() == False

    def test_fix_history_index(self):
        """Test history index fixing."""
        # Setup invalid index
        self.actions.history_index = 10
        self.history.state_history = [{"messages": []}]
        
        # Fix should reset to latest valid index
        self.actions.fix_history_index()
        assert self.actions.history_index == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])