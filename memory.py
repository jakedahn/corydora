from abc import ABC

from langchain.memory.chat_memory import BaseMemory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory.utils import get_prompt_input_key
from langchain.schema import BaseChatMessageHistory, BaseMemory
from langchain.schema.messages import get_buffer_string

from pydantic import Field
from typing import Any, Dict, List, Optional, Tuple


class BaseChatWithSourcesMemory(BaseMemory, ABC):
    chat_memory: BaseChatMessageHistory = Field(default_factory=ChatMessageHistory)
    output_key: Optional[str] = None
    input_key: Optional[str] = None
    return_messages: bool = False

    def _get_input_output(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> Tuple[str, str]:
        if self.input_key is None:
            prompt_input_key = get_prompt_input_key(inputs, self.memory_variables)
        else:
            prompt_input_key = self.input_key
        if self.output_key is None:
            # NOTE(jake): This class is identical to BaseMemory, but I've
            # removed this erroneous check that crashes things if you provide
            # source documents.
            #
            # if len(outputs) != 1:
            #     raise ValueError(f"One output key expected, got {outputs.keys()}")
            output_key = list(outputs.keys())[0]
        else:
            output_key = self.output_key
        return inputs[prompt_input_key], outputs[output_key]

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation to buffer."""
        input_str, output_str = self._get_input_output(inputs, outputs)
        self.chat_memory.add_user_message(input_str)
        self.chat_memory.add_ai_message(output_str)

    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory.clear()


class ConversationWithSourcesBufferMemory(BaseChatWithSourcesMemory):
    """Buffer for storing conversation memory."""

    human_prefix: str = "Human"
    ai_prefix: str = "AI"
    memory_key: str = "history"  #: :meta private:

    @property
    def buffer(self) -> Any:
        """String buffer of memory."""
        if self.return_messages:
            return self.chat_memory.messages
        else:
            return get_buffer_string(
                self.chat_memory.messages,
                human_prefix=self.human_prefix,
                ai_prefix=self.ai_prefix,
            )

    @property
    def memory_variables(self) -> List[str]:
        """Will always return list of memory variables.

        :meta private:
        """
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return history buffer."""
        return {self.memory_key: self.buffer}
