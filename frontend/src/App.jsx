import {
  ChakraProvider,
} from '@chakra-ui/react';
import React from 'react';
import {
  BrowserRouter as Router,
  Route,
  Routes,
} from 'react-router-dom';

import Docs from './components/Docs';
import Game from './components/Game';
import Home from './components/Home';
import ForgotPassword from './components/auth/ForgotPassword';
import Profile from './components/auth/Profile';
import ResetPassword from './components/auth/ResetPassword';
import Reply from './components/Reply';
import SignIn from './components/auth/SignIn';
import SignOut from './components/auth/SignOut';
import SignUp from './components/auth/SignUp';
import Team from './components/Team';
import TagManager from 'react-gtm-module';

const tagManagerArgs = {
    gtmId: 'GTM-PKF2HNB'
};
TagManager.initialize(tagManagerArgs)

function App() {
  return (
    <ChakraProvider>
      <Router>
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/docs' element={<Docs />} />
          <Route path='/home' element={<Home />} />
          <Route path='/game/:game_id/for-team/:team_id' element={<Game />} />
          <Route path='/forgot-password' element={<ForgotPassword />} />
          <Route path='/profile' element={<Profile />} />
          <Route path='/reset-password' element={<ResetPassword />} />
          <Route path='/reply/:game_id/:team_id/:user_id/:response' element={<Reply />} />
          <Route path='/sign-in' element={<SignIn />} />
          <Route path='/sign-out' element={<SignOut />} />
          <Route path='/sign-up' element={<SignUp />} />
          <Route path='/team/:team_name_or_id' element={<Team />} />
          <Route path='/team/' element={<Team />} />
        </Routes>
      </Router>
    </ChakraProvider>
  );
}

export default App;
