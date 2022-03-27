import React from 'react';
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
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';

function About() {
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
              Marketing, marketing...
            </Text>
            <Link
              color="green.500"
              href="/games"
              fontSize="2xl"
              rel="noopener noreferrer"
            >
              My Games
            </Link>
            <Link
              color="green.500"
              href="/sign-in"
              fontSize="2xl"
              rel="noopener noreferrer"
            >
              Sign In
            </Link>
          </VStack>
        </Grid>
      </Box>
    </ChakraProvider>
  );
}

export default About;
