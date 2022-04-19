import { CalendarIcon, DownloadIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Box,
  Center,
  ChakraProvider,
  theme,
  useColorModeValue,
} from '@chakra-ui/react';
import React, {useEffect, useRef, useState} from 'react';
import { useNavigate, useParams } from "react-router-dom";
import TagManager from 'react-gtm-module'
import _ from "lodash";

import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData } from '../utils';


export default function Schedule() {

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
      checkLogin(null).then(result => { setUser(result) });

      fetchedData.current = true;
    }
  });

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate} signed_in={_.has(user, 'user_id', false)}></Header>
      <Center height='80vh'>
        <iframe overflow='hidden' height='100%' width='100%' src="https://stats.sharksice.timetoscore.com/display-stats.php?league=1" title="W3Schools Free Online Web Tutorials"></iframe>
      </Center>
      <Footer></Footer>
    </ChakraProvider>
  );
}
