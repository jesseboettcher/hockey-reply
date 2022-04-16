import { Box, IconButton, Link, Tooltip, useColorMode, useColorModeValue } from '@chakra-ui/react';
import React from 'react';

export function ButtonWithTip(props: React.PropsWithChildren<MyProps>) {

  const tipBackground = useColorModeValue('#EDF2F7', '#2C313D');
  const tipTextColor = useColorModeValue('gray.500', 'gray.200');

  return (
      <Tooltip label={props.label} placement={props.placement} bg={tipBackground} color={tipTextColor} openDelay={500}>
        <Box>
        { props.linkDownloadAction &&
          <Link onClick={props.linkDownloadAction} target='_blank' download>
            <IconButton ml={3} mr={props.mr} mb='3px' size='xs' icon={props.icon}/>
          </Link>
        }
        { props.href &&
          <Link href={props.href}>
            <IconButton ml={3} mr={props.mr} mb='3px' size='xs' icon={props.icon}/>
          </Link>
        }
        </Box>
      </Tooltip>
    );
};