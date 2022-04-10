import {
  Box,
  Center,
  ChakraProvider,
  theme,
  useColorModeValue,
} from '@chakra-ui/react';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import React, {useEffect, useRef, useState} from 'react';
import { useNavigate, useParams } from "react-router-dom";
import { checkLogin, getAuthHeader, getData } from '../utils';
import TagManager from 'react-gtm-module'
import ReactMarkdown from 'react-markdown'

export default function Docs() {

  let navigate = useNavigate();
  const fetchedData = useRef(false);
  const [user, setUser] = useState({});

  useEffect(() => {
    if (!fetchedData.current) {
      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Home',
        },
      });
      checkLogin(navigate).then(result => { setUser(result) });

      fetchedData.current = true;
    }


  });

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate} signed_in={user != {}}></Header>
      <Box minH='300px' mt={10} mx={{ base:'20px', md:'50px'}}>
          <ReactMarkdown>
            *React-Markdown* is **Awesome**
          </ReactMarkdown>
      </Box>
      <Footer></Footer>
    </ChakraProvider>
  );
}