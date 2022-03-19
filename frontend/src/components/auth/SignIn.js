import {
  Flex,
  Box,
  FormControl,
  FormLabel,
  Input,
  Checkbox,
  Stack,
  Link,
  Button,
  Heading,
  Text,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from "react-router-dom";

export default function SignIn() {

  let navigate = useNavigate();
  const emailRef = React.useRef();
  const passwordRef = React.useRef();
  const toast = useToast();

  const keyboardHandler = async event => {
    console.log(event.target);
  };
  const submitSignIn = async event => {

    // TODO hash password before sending (HR-7)
    let data = {
      email: emailRef.current.value,
      password: passwordRef.current.value,
    };

    fetch("/api/sign-in", {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        navigate('/games', {replace: true});
        return;
      }
      toast({
          title: `Sign in failed`,
          status: 'error', isClosable: true,
      })
    });
  };

 useEffect(() => {
    const listener = event => {
      if (event.code === "Enter" || event.code === "NumpadEnter") {
        submitSignIn();
      }
    };
    document.addEventListener("keyup", listener);
    return () => {
      document.removeEventListener("keyup", listener);
    };
  }, []);

  return (
    <Flex
      minH={'100vh'}
      align={'center'}
      justify={'center'}
      bg={useColorModeValue('gray.50', 'gray.800')}>
      <Stack spacing={8} mx={'auto'} maxW={'lg'} py={12} px={6}>
        <Stack align={'center'}>
          <Heading fontSize={'4xl'}>Sign in to Hockey Reply</Heading>
        </Stack>
        <Box
          rounded={'lg'}
          bg={useColorModeValue('white', 'gray.700')}
          boxShadow={'lg'}
          p={8}>
          <Stack spacing={4}>

            <FormControl id="email">
              <FormLabel>Email address</FormLabel>
              <Input type="email" ref={emailRef} />
            </FormControl>

            <FormControl id="password">
              <FormLabel>Password</FormLabel>
              <Input type="password" ref={passwordRef} />
            </FormControl>

            <Stack spacing={10}>
              <Stack
                direction={{ base: 'column', sm: 'row' }}
                align={'start'}
                justify={'space-between'}>
                <Link color={'blue.400'} href='/forgot-password'>Forgot password?</Link>
              </Stack>
              <Button
                bg={'blue.400'}
                color={'white'}
                _hover={{ bg: 'blue.500', }}
                onClick={submitSignIn}>
                Sign in
              </Button>
              <p>Need an account? <Link color={'blue.400'} href='/sign-up'>Sign up ></Link></p>
            </Stack>

          </Stack>
        </Box>
      </Stack>
    </Flex>
  );
  }