import {
  Box,
  Button,
  Input,
  InputGroup,
  InputRightElement,
  Stack,
  Text,
  VStack,
  Popover,
  PopoverTrigger,
  PopoverContent,
  useColorModeValue,
  IconButton,
  HStack,
} from '@chakra-ui/react';
import { DeleteIcon, EditIcon } from '@chakra-ui/icons'
import React, { useState } from 'react';
import dayjs from 'dayjs';
import EmojiPicker from 'emoji-picker-react';
import Markdown from 'markdown-to-jsx';
import { useParams } from "react-router-dom";
import { getAuthHeader } from '../utils';

export default function Chat({ messages, setMessages, players, user }) {
  const [newMessage, setNewMessage] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editMessageContent, setEditMessageContent] = useState('');

  // Add game_id and team_id from params
  const { game_id, team_id } = useParams();

  // Color mode values
  const messageBg = useColorModeValue('gray.50', 'gray.700');
  const nameColor = useColorModeValue('red.500', 'red.200');
  const userNameColor = useColorModeValue('blue.500', 'blue.200');
  const timeColor = useColorModeValue('gray.400', 'gray.500');
  const messageColor = useColorModeValue('gray.800', 'gray.100');
  const deleteButtonScheme = useColorModeValue('blackAlpha', 'red');
  const emojiPickerScheme = useColorModeValue('light', 'dark');

  const formatTimestamp = (timestamp) => {
    return dayjs(timestamp * 1000).format('ddd MMM D @ h:mm A');
  };

  // Group reactions by emoji and count them
  const getReactionCounts = (reactions) => {
    return reactions.reduce((acc, reaction) => {
      acc[reaction.emoji] = acc[reaction.emoji] || { count: 0, users: [] };
      acc[reaction.emoji].count += 1;
      acc[reaction.emoji].users.push(reaction.user_id);
      return acc;
    }, {});
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!newMessage.trim()) return;

    const data = {
      game_id: game_id,
      team_id: team_id,
      content: newMessage,
      user_id: user.user_id
    };

    fetch(`/api/chat/message`, {
      method: "POST",
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json', 
        'Authorization': getAuthHeader()
      },
      body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
      if (result.message_id) {
        // Create new message object
        const newMessageObj = {
          message_id: result.message_id,
          user_id: user.user_id,
          content: newMessage,
          created_at: Date.now() / 1000,
          edited_at: null,
          reactions: []
        };
        
        // Update messages state with new message
        setMessages([...messages, newMessageObj]);
        
        // Clear input after successful send
        setNewMessage('');
      }
    })
    .catch(error => {
      console.error('Error sending message:', error);
    });
  };

  const handleReaction = (messageId, emoji) => {
    const data = {
      message_id: messageId,
      emoji: emoji
    };

    // Check if user has already reacted with this emoji
    const message = messages.find(m => m.message_id === messageId);
    console.log('reaction msg', message);
    const existingReaction = message.reactions && message.reactions.find(
      r => r.emoji === emoji && r.user_id === user.user_id
    );

    const method = existingReaction ? "DELETE" : "POST";

    fetch('/api/chat/reaction', {
      method: method,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': getAuthHeader()
      },
      body: JSON.stringify(data)
    })
      .then(response => {
        if (response.status === 200) {
          // Update local state
          setMessages(messages.map(msg => {
            if (msg.message_id === messageId) {
              if (existingReaction) {
                // Remove reaction
                return {
                  ...msg,
                  reactions: msg.reactions.filter(
                    r => !(r.emoji === emoji && r.user_id === user.user_id)
                  )
                };
              } else {
                // Add reaction
                return {
                  ...msg,
                  reactions: [...msg.reactions, {
                    emoji: emoji,
                    user_id: user.user_id,
                    created_at: Date.now() / 1000
                  }]
                };
              }
            }
            return msg;
          }));
        }
      })
      .catch(error => {
        console.error('Error toggling reaction:', error);
      });
  };

  const handleDelete = (messageId) => {
    const data = {
      game_id: game_id,
      team_id: team_id,
      message_id: messageId,
      user_id: user.user_id
    };

    fetch(`/api/chat/message/${messageId}`, {
      method: "DELETE",
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': getAuthHeader()
      },
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status === 200) {
        // Remove the message from local state
        setMessages(messages.filter(msg => msg.message_id !== messageId));
        return;
      }
    })
    .catch(error => {
      console.error('Error deleting message:', error);
    });
  };

  const handleEdit = (messageId, content) => {
    if (editingMessageId === messageId) {
      // Save the edit
      const data = {
        game_id: game_id,
        team_id: team_id,
        message_id: messageId,
        content: editMessageContent,
        user_id: user.user_id
      };

      fetch(`/api/chat/message/${messageId}`, {
        method: "PUT",
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': getAuthHeader()
        },
        body: JSON.stringify(data)
      })
      .then(response => {
        if (response.status === 200) {
          // Update the message in local state
          setMessages(messages.map(msg => {
            if (msg.message_id === messageId) {
              return {
                ...msg,
                content: editMessageContent,
                edited_at: Date.now() / 1000
              };
            }
            return msg;
          }));
          
          // Clear editing state
          setEditingMessageId(null);
          setEditMessageContent('');
        }
      })
      .catch(error => {
        console.error('Error editing message:', error);
      });
    } else {
      // Enter edit mode
      setEditingMessageId(messageId);
      setEditMessageContent(content);
    }
  };

  return (
    <Box 
      p={0}
      >
      {/* Messages Container */}
      <VStack 
        align="stretch" 
        spacing={4} 
        mb={4}
      >
        {messages.map((message) => (
          <Box 
            key={message.message_id}
            bg={messageBg}
            p={3}
            borderRadius="md"
            alignSelf={message.user_id === user.user_id ? 'flex-end' : 'flex-start'}
            minW="100%"
          >
            <Stack direction="row" justify="space-between" mb={1}>
              <Text fontSize="sm" fontWeight="bold" color={message.user_id === user.user_id ? userNameColor : nameColor}>
                {players[message.user_id]}
              </Text>
              <HStack spacing={2}>
                <IconButton
                  icon={<EditIcon />}
                  size="xs"
                  variant="ghost"
                  visibility={message.user_id === user.user_id ? 'visible' : 'hidden'}
                  colorScheme={deleteButtonScheme}
                  opacity="0.6"
                  _hover={{ opacity: 1 }}
                  onClick={() => handleEdit(message.message_id, message.content)}
                  aria-label="Edit message"
                />
                <IconButton
                  icon={<DeleteIcon />}
                  size="xs"
                  variant="ghost"
                  visibility={message.user_id === user.user_id ? 'visible' : 'hidden'}
                  colorScheme={deleteButtonScheme}
                  opacity="0.6"
                  _hover={{ opacity: 1 }}
                  onClick={() => handleDelete(message.message_id)}
                  aria-label="Delete message"
                />
                <Text fontSize="xs" color={timeColor}>
                  {formatTimestamp(message.created_at)}
                </Text>
              </HStack>
            </Stack>
            {editingMessageId === message.message_id ? (
              <form onSubmit={(e) => {
                e.preventDefault();
                handleEdit(message.message_id, message.content);
              }}>
                <InputGroup size="sm">
                  <Input
                    value={editMessageContent}
                    onChange={(e) => setEditMessageContent(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setEditingMessageId(null);
                        setEditMessageContent('');
                      }
                    }}
                    autoFocus
                  />
                  <InputRightElement width="4.5rem">
                    <Button h="1.5rem" size="xs" type="submit">
                      Save
                    </Button>
                  </InputRightElement>
                </InputGroup>
              </form>
            ) : (
              <Box>
                <Text lineHeight="1.3" fontSize="0.8em" color={messageColor}>
                  <Markdown>{message.content}</Markdown>
                </Text>
                {message.edited_at && (
                  <Text fontSize="xs" color={timeColor} mt={1}>
                    (edited)
                  </Text>
                )}
              </Box>
            )}
        
            {message.reactions.length > 0 && (
              <Stack direction="row" mt={2} spacing={1} wrap="wrap">
                {Object.entries(getReactionCounts(message.reactions)).map(([emoji, data]) => (
                  <Button
                    key={emoji}
                    size="xs"
                    variant={data.users.includes(user.user_id) ? "outline" : "solid"}
                    colorScheme={data.users.includes(user.user_id) ? "blue" : "gray"}
                    onClick={() => handleReaction(message.message_id, emoji)}
                    py={0}
                    height="27px"
                    minW="45px"
                    fontSize=".9em"
                  >
                    {emoji} <Text as="span" ml={2} fontSize="0.8em">{data.count}</Text>
                  </Button>
                ))}
                <Popover
                  isOpen={showEmojiPicker && selectedMessageId === message.message_id}
                  onClose={() => {
                    setShowEmojiPicker(false);
                    setSelectedMessageId(null);
                  }}
                  placement="top-start"  // Controls initial placement
                  offset={[-20, 10]}    // [horizontal, vertical] offset
                  gutter={20}           // Space between trigger and popup
                  closeOnBlur={false}
                >
                  <PopoverTrigger>
                    <Button
                      size="xs"
                      variant="ghost"
                      colorScheme="gray"
                      onClick={() => {
                        if (!selectedMessageId) {
                          setSelectedMessageId(message.message_id);
                          setShowEmojiPicker(true);
                        }
                        else if (selectedMessageId === message.message_id) {
                          setShowEmojiPicker(false);
                          setSelectedMessageId(null);
                        }
                        else {
                          setSelectedMessageId(message.message_id);
                          setShowEmojiPicker(true);
                        }
                      }}
                      height="27px"
                    >
                      +
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent width="350px">  {/* Control the width explicitly */}
                    <EmojiPicker
                      onEmojiClick={(emojiData) => {
                        handleReaction(message.message_id, emojiData.emoji);
                        setShowEmojiPicker(false);
                        setSelectedMessageId(null);
                      }}
                      width="100%"
                      height="350px"
                      theme={emojiPickerScheme}
                    />
                  </PopoverContent>
                </Popover>
              </Stack>
            )}
            {/* Show emoji picker for messages with no reactions yet */}
            {message.reactions.length === 0 && (
              <Popover
                isOpen={showEmojiPicker && selectedMessageId === message.message_id}
                onClose={() => {
                  setShowEmojiPicker(false);
                  setSelectedMessageId(null);
                }}
                placement="top-start"  // Controls initial placement
                offset={[-20, 10]}    // [horizontal, vertical] offset
                gutter={20}           // Space between trigger and popup
                closeOnBlur={false}
              >
                <PopoverTrigger>
                  <Button
                    size="xs"
                    variant="ghost"
                    colorScheme="gray"
                    onClick={() => {
                      if (!selectedMessageId) {
                        setSelectedMessageId(message.message_id);
                        setShowEmojiPicker(true);
                      }
                      else if (selectedMessageId === message.message_id) {
                        setShowEmojiPicker(false);
                        setSelectedMessageId(null);
                      }
                      else {
                        setSelectedMessageId(message.message_id);
                        setShowEmojiPicker(true);
                      }
                    }}
                    py={0}
                    height="27px"
                  >
                    +
                  </Button>
                </PopoverTrigger>
                <PopoverContent width="350px">  {/* Control the width explicitly */}
                  <EmojiPicker
                    onEmojiClick={(emojiData) => {
                      handleReaction(message.message_id, emojiData.emoji);
                      setShowEmojiPicker(false);
                      setSelectedMessageId(null);
                    }}
                    width="100%"
                    height="350px"
                    theme={emojiPickerScheme}
                  />
                </PopoverContent>
              </Popover>
            )}
          </Box>
        ))}
      </VStack>

      <form onSubmit={handleSubmit}>
        <InputGroup size="md">
          <Input
            pr="4.5rem"
            type="text"
            placeholder="Message..."
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
          />
          <InputRightElement width="4.5rem">
            <Button h="1.75rem" size="sm" type="submit">
              Send
            </Button>
          </InputRightElement>
        </InputGroup>
      </form>
    </Box>
  );
}