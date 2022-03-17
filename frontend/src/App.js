import React from 'react';
import {
  ChakraProvider,
} from '@chakra-ui/react';
import {
  BrowserRouter as Router,
  Route,
  Routes,
} from 'react-router-dom';

import Home from './components/Home';
import ForgotPassword from './components/auth/ForgotPassword'
import SignIn from './components/auth/SignIn';
import SignUp from './components/auth/SignUp'

function App() {
  return (
    <ChakraProvider>
      <Router>
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/forgot-password' element={<ForgotPassword />} />
          <Route path='/sign-in' element={<SignIn />} />
          <Route path='/sign-up' element={<SignUp />} />
        </Routes>
      </Router>
    </ChakraProvider>
  );
}

export default App;
