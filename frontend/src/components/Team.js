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

function Team() {

  let { team_id } = useParams();
  let navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const fetchedData = useRef(false);

  useEffect(() => {
    checkLogin(navigate);

    let url;
    if (team_id === undefined) {
      url = `/api/teams?all=1`;
    }
    else {
      url = `/api/team/${team_id}`;
    }

    if (!fetchedData.current) {
      fetch(url, {credentials: 'include'})
      .then(r =>  r.json().then(data => ({status: r.status, body: data})))
        .then(obj => { setTeams( obj.body['teams']) });

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

        </Grid>
      </Box>
    </ChakraProvider>
  );
}

export default Team;
