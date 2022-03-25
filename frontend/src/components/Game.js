import React, {useEffect, useRef, useState} from 'react';
import {
  Center,
  ChakraProvider,
  Container,
  Badge,
  Box,
  Button,
  GridItem,
  Flex,
  Input,
  InputGroup,
  InputRightElement,
  Text,
  Link,
  List,
  ListIcon,
  ListItem,
  VStack,
  Code,
  Grid,
  theme,
  Select,
  SimpleGrid,
  Stack,
  StackDivider,
  Spacer,
  Wrap,
  WrapItem,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import {
  Table,
  Thead,
  Tbody,
  Tfoot,
  Tr,
  Th,
  Td,
  TableCaption,
} from "@chakra-ui/react"
import { ArrowForwardIcon } from '@chakra-ui/icons'
import { useNavigate, useParams } from "react-router-dom";
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { checkLogin } from '../utils';

function getData(url, arrayName, setFn) {
    fetch(url, {credentials: 'include'})
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => { return setFn(obj.body[arrayName][0]) });
}

function InfoBox(props: React.PropsWithChildren<MyProps>) {
  const bg = useColorModeValue('brand.500', 'teal')
  const infoBoxColor = useColorModeValue('#F0F8FE', '#303841')
  const infoBoxBorderColor = useColorModeValue('#DDE5EB', '#495563')
  console.log(bg)
  return (
    <Box textAlign="left"
         fontSize="0.8em"
         bg={infoBoxColor}
         borderColor={infoBoxBorderColor}
         borderWidth='1px'
         borderRadius='10px'
         p="10px"
         mr="20px">
         {props.children}
    </Box>

    )
}

function Game() {

  let { game_id } = useParams();
  let navigate = useNavigate();
  const [game, setGame] = useState([]);
  const fetchedData = useRef(false);
  const toast = useToast();

  useEffect(() => {
    checkLogin(navigate);

    if (!fetchedData.current) {
      console.log(`/api/game/${game_id}`)
      getData(`/api/game/${game_id}`, 'games', setGame);
      console.log(game)
      fetchedData.current = true;
    }
  });
  const bg = useColorModeValue('brand.500', 'teal')

  return (
    <ChakraProvider theme={theme}>
      <Box textAlign="center" fontSize="xl" mt="50px">
          <SimpleGrid maxW="1200px" columns={2} minChildWidth='300px' spacing='40px' mx='auto'>
            <InfoBox>
              <Text>TIME: {game['scheduled_at']}</Text>
              <Text>RINK: {game['rink']}</Text>
              <Text>VS: {game['away_team_name']}</Text>
              <Text>&nbsp;</Text>
              <Text>Players: 9 + (2 maybe)</Text>
              <Text>Goalie: Yes</Text>
            </InfoBox>

            <Box textAlign="left" p="10px" ml="20px">
              <Text fontSize="0.8em" mb="8px">Update your status:</Text>
              <Button colorScheme='green' size='sm' mr="15px">
                YES
              </Button>
              <Button colorScheme='blue' size='sm' mr="15px">
                Maybe
              </Button>
              <Button colorScheme='red' size='sm'>
                NO
              </Button>

              <InputGroup size='md' mt="28px">
                <Input
                  pr='4.5rem'
                  type='text'
                  placeholder='Message'
                />
                <InputRightElement width='4.5rem'>
                  <Button h='1.75rem' size='sm'>
                    Send
                  </Button>
                </InputRightElement>
              </InputGroup>
            </Box>

          </SimpleGrid>

          <Center>
            <Table size="sml" maxWidth="1200px" mt="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="25%">Player</Th>
                  <Th w="10%">Reply</Th>
                  <Th w="75%">Message</Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                <Tr>
                  <Td py="6px">Jesse (full)</Td>
                  <Td>
                    <Badge colorScheme="green" >YES</Badge>
                  </Td>
                  <Td>Are we getting beer tonight?</Td>
                </Tr>
                <Tr>
                  <Td py="6px">Travis (full)</Td>
                  <Td>
                    <Badge colorScheme="red">NO</Badge>
                  </Td>
                  <Td>I like candy</Td>
                </Tr>
                <Tr>
                  <Td py="5px">Rob (half)</Td>
                  <Td>
                    <Badge colorScheme="blue">Maybe</Badge>
                  </Td>
                  <Td>Driving my car</Td>
                </Tr>
              </Tbody>
            </Table>
          </Center>

          <Center>
            <Table size="sml" maxWidth="1200px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="25%">No Reply</Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                <Tr>
                  <Td py="6px">Jim (full)</Td>
                </Tr>
                <Tr>
                  <Td py="6px">Vic (full)</Td>
                </Tr>
                <Tr>
                  <Td py="5px">JP (sub)</Td>
                </Tr>
              </Tbody>
            </Table>
          </Center>

          <ColorModeSwitcher justifySelf="flex-end" />
      </Box>
    </ChakraProvider>
  );
}

export default Game;
