import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  Input,
  Link,
  Stack,
  Text,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import queryString from 'query-string'
import React, { useEffect, useState, useRef } from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useSearchParams } from "react-router-dom";

import { Header } from '../Header';
import { Footer } from '../Footer';

export default function SignIn() {

  let redirect_path = queryString.parse(window.location.search).redirect;
  const [searchParams, setSearchParams] = useSearchParams();
  let navigate = useNavigate();
  const emailRef = React.useRef();
  const passwordRef = React.useRef();
  const toast = useToast();
  const fetchedData = useRef(false);

  const submitSignIn = async event => {

    event.preventDefault();

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
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
    .then(obj => {
      if (obj.status == 200) {

        if (obj.body.token) {
          window.localStorage.setItem('token', obj.body.token);
        }

        if (redirect_path) {
          navigate(redirect_path, {replace: true});
        }
        else {
          navigate('/home', {replace: true});
        }
        return;
      }
      toast({
          title: `Sign in failed`,
          status: 'error', isClosable: true,
      })
    });
  };

  useEffect(() => {
    if (!fetchedData.current) {
      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Sign In',
        },
      });
      fetchedData.current = true;
    }
  });

  const url_event = searchParams.get("event")
  let password_update_msg = null
  if (url_event == "password_updated") {
    password_update_msg = <p>Your password has been updated. Please sign in.</p>
  }

  return (
    <Box >
    <Header hide_sign_in={true} />
    <Flex
      minH={'10vh'}
      align={'center'}
      justify={'center'}>
      <Stack spacing={8} mx={'auto'} maxW={'lg'} minW={'md'} py={12} px={6}>
        <Box
          rounded={'lg'}
          bg={useColorModeValue('white', 'gray.700')}
          boxShadow={'lg'}
          p={8}>
          <form onSubmit={submitSignIn}>
            <Stack spacing={4}>
              {password_update_msg}
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
                  type="submit">
                  Sign in
                </Button>
                <p>Need an account? <Link color={'blue.400'} href='/sign-up'>Sign up ></Link></p>
              </Stack>
            </Stack>
          </form>
        </Box>
      </Stack>
    </Flex>
    <Footer/>
    </Box>
  );
}
