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

  useEffect(() => {

    if (!fetchedData.current) {
      checkLogin(navigate).then(result => { setUser(result) });

      getData('/api/team/', setMyTeams)
      getData('/api/team/?all=1', setTeams)
      getData('/api/games/?upcomingOnly', setMyGames)

      fetchedData.current = true;
    }
  });

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
                        <a href={`/game/${game.game_id}/for-team/${game.home_team_id}`}>
                          vs {game.vs} >
                        </a></Td>
                      <Td py="6px">{game.scheduled_at}</Td>
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
              </Tbody>
            </Table>
          </Center>
      </Box>
      <Footer></Footer>
    </ChakraProvider>
  );
}

export default Home;
