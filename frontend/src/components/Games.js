import React, {useEffect} from 'react';
import {
  ChakraProvider,
  Box,
  Text,
  Link,
  VStack,
  Code,
  Grid,
  theme,
} from '@chakra-ui/react';
import { useNavigate } from "react-router-dom";
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { checkLogin } from '../utils';

function delete_cookie(name) {
  document.cookie = name+'=; Max-Age=-99999999;';
}

function Games() {

  let navigate = useNavigate();

  useEffect(() => {
    checkLogin(navigate);
  });

  const logout = async event => {
    delete_cookie('user');
    navigate('/', {replace: true})
  }

  return (
    <ChakraProvider theme={theme}>
      <Box textAlign="center" fontSize="xl">
        <Grid minH="100vh" p={3}>
          <ColorModeSwitcher justifySelf="flex-end" />
          <VStack spacing={8}>
            <Text>
              Welcome to <Code fontSize="xl">HockeyReply</Code>!
            </Text>
            <Text>
              Here are your games
            </Text>
            <Link
              color="green.500"
              fontSize="2xl"
              rel="noopener noreferrer"
              onClick={logout}>
            >
              Log out
            </Link>
          </VStack>
        </Grid>
      </Box>
    </ChakraProvider>
  );
}

export default Games;
