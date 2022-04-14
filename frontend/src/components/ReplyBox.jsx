import { EditIcon } from '@chakra-ui/icons';
import {
  Badge,
  Box,
  Button,
  Checkbox,
  Input,
  InputGroup,
  InputRightElement,
  Popover,
  PopoverArrow,
  PopoverContent,
  PopoverCloseButton,
  PopoverTrigger,
  Text,
  VStack,
  useColorMode,
  useColorModeValue,
} from '@chakra-ui/react';
import React from 'react';
import { FaMoon, FaSun } from 'react-icons/fa';

export function ReplyBox(props: React.PropsWithChildren<MyProps>) {

  let replyBadge = {};
  let editIcon = props.editable ? <EditIcon mr="4px" mb="2px" /> : null;
  let openHandler = props.editable ? props.openHandler : null;

  replyBadge[''] = <Badge colorScheme="gray" width='80px' my="0px">&nbsp;&nbsp;{editIcon}</Badge>;
  replyBadge['yes'] = <Badge colorScheme="green" width='80px' my="0px">{editIcon}YES</Badge>;
  replyBadge['no'] = <Badge colorScheme="red" width='80px' my="0px">{editIcon}NO</Badge>;
  replyBadge['maybe'] = <Badge colorScheme="blue" width='80px'  my="0px">{editIcon}Maybe</Badge>;

  return (
          <Popover isOpen={props.isOpen}>
            <PopoverTrigger>
              <Button size='xs' bg='transparent' onClick={openHandler}>{replyBadge[props.user_reply]}</Button>
            </PopoverTrigger>
            <PopoverContent width='auto' p={2} >
                <PopoverArrow />
                <PopoverCloseButton onClick={props.closeHandler} />

                <Box textAlign="center" p="10px" mx="00px">
                  <VStack spacing='0px' mt={0}>
                    <Box>
                  { props.name &&
                    <Text fontSize="0.8em" mb="8px">Update status for {props.name}:</Text>
                  }
                  { !props.name &&
                    <Text fontSize="0.8em" mb="8px">Update your status:</Text>
                  }
                  <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => props.submitHandler(e, props.user_id, props.team_id, props.game_id, 'yes', null)}>
                    YES
                  </Button>
                  <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => props.submitHandler(e, props.user_id, props.team_id, props.game_id, 'maybe', null)}>
                    Maybe
                  </Button>
                  <Button colorScheme='red' size='sm' onClick={(e) => props.submitHandler(e, props.user_id, props.team_id, props.game_id, 'no', null)}>
                    NO
                  </Button>
                  </Box>
                  <Box>
                  {props.goalie &&
                    <Checkbox ml={0} mt={4} colorScheme='green' isChecked={props.is_goalie} onChange={(e) => props.submitHandler(e, props.user_id, props.team_id, props.game_id, null, null, e.target.checked)}>
                      Goalie?
                    </Checkbox>
                  }
                  </Box>

                  { props.message &&
                    <form onSubmit={(e) => props.submitHandler(e, props.user_id, props.team_id, props.game_id, null, props.message)}>
                      <InputGroup size='md' mt={4}>
                        <Input
                          pr='4.5rem'
                          type='text'
                          placeholder='Message'
                          onChange={(e) => props.setMessage(e.target.value)}
                          key="main"
                        />
                        <InputRightElement width='4.5rem'>
                          <Button h='1.75rem' size='sm' type="submit">
                            Send
                          </Button>
                        </InputRightElement>
                      </InputGroup>
                    </form>
                  }
                  </VStack>
                </Box>
              </PopoverContent>
            </Popover>
          )
}