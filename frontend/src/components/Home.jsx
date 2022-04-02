import React, {useEffect, useRef, useState} from 'react';
import {
  Center,
  ChakraProvider,
  Box,
  Divider,
  Flex,
  Text,
  Link,
  HStack,
  VStack,
  Modal,
  useDisclosure,
  finalRef,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  FormControl,
  FormLabel,
  Input,
  ModalFooter,
  Button,
  Code,
  Grid,
  Spacer,
  Square,
  Table,
  Tbody,
  Td,
  Thead,
  Th,
  Tr,
  theme,
  useColorModeValue,
} from '@chakra-ui/react';
import { useNavigate, useParams } from "react-router-dom";
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getData, logout, MyLink } from '../utils';

function Home() {

  let navigate = useNavigate();
  const fetchedData = useRef(false);
  const [myTeams, setMyTeams] = useState([]);
  const [teams, setTeams] = useState([]);
  const [myGames, setMyGames] = useState([]);
  const [user, setUser] = useState({});
  const joinTeamRef = React.useRef();

  const { isOpen, onOpen, onClose } = useDisclosure()

  useEffect(() => {

    if (!fetchedData.current) {
      checkLogin(navigate).then(result => { setUser(result) });

      getData('/api/team/', setMyTeams)
      getData('/api/team/?all=1', setTeams)
      getData('/api/games/?upcomingOnly', setMyGames)

      fetchedData.current = true;
    }
  });

  function joinTeam() {
    let data = {
      team_name: joinTeamRef.current.value,
      user_id: user['user_id'],
    };

    fetch(`/api/join-team`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        // TODO smarter refresh
        window.location.reload(false);
        return;
      }
    });
    onClose();
  };


  return (
    <ChakraProvider theme={theme}>

      <Header react_navigate={navigate} signed_in={user != {}}></Header>

      <Box fontSize="xl">
          <Center>
            <Table size="sml" maxWidth="1200px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="50%">My Games</Th>
                  <Th/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  myGames['games'] && myGames['games'].map((game) => (

                    <Tr key={game.game_id}>
                      <Td py="6px">
                        <a href={`/game/${game.game_id}/for-team/${game.user_team_id}`}>
                          vs {game.vs} >
                        </a></Td>
                      <Td py="6px">{game['scheduled_at']} (in&nbsp;{game['scheduled_how_soon']})</Td>
                    </Tr>
                 ))
                }
              </Tbody>
            </Table>
          </Center>
          <Center>
            <Table size="sml" maxWidth="1200px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="25%">My Teams</Th>
                  <Th/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  myTeams['teams'] && myTeams['teams'].map((team) => (

                    <Tr key={team.team_id}>
                      <Td py="6px"><a href={`/team/${team.team_id}`}>{team.name} ></a></Td>
                      <Td py="6px"></Td>
                    </Tr>
                 ))
                }
                <Tr>
                 &nbsp;
                </Tr>
                <Tr>
                  <Button size='sm' onClick={onOpen}>Join a Team</Button>
                </Tr>
              </Tbody>
            </Table>
          </Center>
      </Box>

      <Modal
              isOpen={isOpen}
              onClose={onClose}
            >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Join a team</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <FormControl>
              <Input ref={joinTeamRef} placeholder='Team name' />
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button onClick={e => joinTeam()} colorScheme='blue' mr={3}>
              Join
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Footer></Footer>
    </ChakraProvider>
  );
}

export default Home;
