import React from 'react';
import {
  ChakraProvider,
} from '@chakra-ui/react';
import {
  BrowserRouter as Router,
  Route,
  Routes,
} from 'react-router-dom';

import Game from './components/Game'
import Games from './components/Games'
import Home from './components/Home';
import ForgotPassword from './components/auth/ForgotPassword'
import ResetPassword from './components/auth/ResetPassword'
import SignIn from './components/auth/SignIn';
import SignUp from './components/auth/SignUp'
import Team from './components/Team'

function App() {
  return (
    <ChakraProvider>
      <Router>
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/game/:game_id/for-team/:team_id' element={<Game />} />
          <Route path='/games' element={<Games />} />
          <Route path='/forgot-password' element={<ForgotPassword />} />
          <Route path='/reset-password' element={<ResetPassword />} />
          <Route path='/sign-in' element={<SignIn />} />
          <Route path='/sign-up' element={<SignUp />} />
          <Route path='/team/:team_id' element={<Team />} />
          <Route path='/team/' element={<Team />} />
        </Routes>
      </Router>
    </ChakraProvider>
  );
}

export default App;
