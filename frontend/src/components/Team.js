import React, {useEffect, useRef, useState} from 'react';
import {
  ChakraProvider,
  Box,
  Text,
  Link,
  List,
  ListIcon,
  ListItem,
  VStack,
  Code,
  Grid,
  theme,
} from '@chakra-ui/react';
import { useNavigate, useParams } from "react-router-dom";
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { checkLogin } from '../utils';

function getData(url, arrayName, setFn) {
    fetch(url, {credentials: 'include'})
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => { return setFn(obj.body[arrayName]) });
}

function Team() {

  let { team_id } = useParams();
  let navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [joinRequests, setJoinRequests] = useState([]);
  const fetchedData = useRef(false);

  useEffect(() => {
    checkLogin(navigate);

    if (!fetchedData.current) {
      if (team_id === undefined) {
        getData('/api/team/', 'teams', setTeams);
        getData('/api/join-requests/', 'join_requests', setJoinRequests);
      }
      else {
        getData(`/api/team/${team_id}`, 'teams', setTeams);
        getData(`/api/join-requests/${team_id}`, 'join_requests', setJoinRequests);
      }
      fetchedData.current = true;
    }
  });

  return (
    <ChakraProvider theme={theme}>
      <Box textAlign="center" fontSize="xl">
        <Grid minH="100vh" p={3}>
          <ColorModeSwitcher justifySelf="flex-end" />
            
            <List spacing={3}>
              { teams.map((team) => (
                <ListItem key={team.team_id}>
                  <ListIcon  color='green.500' />
                  {team.name} ({team.player_count} players)
                </ListItem>
               ))
              }
            </List>
            <List spacing={3}>
              { joinRequests.map((request) => (
                <ListItem key={request.email}>
                  <ListIcon  color='green.500' />
                  {request.email} ({request.requested_at})
                </ListItem>
               ))
              }
            </List>


        </Grid>
      </Box>
    </ChakraProvider>
  );
}

export default Team;
