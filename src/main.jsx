import React from'react';
import{createRoot}from'react-dom/client';
import ProductionApp from'./ProductionApp';
import TerminalEnhancements from'./TerminalEnhancements';
import'./style.css';
import'./institution.css';
import'./equity.css';
import'./production.css';
import'./ndr-layout.css';
import'./news-prediction.css';

createRoot(document.getElementById('root')).render(<><ProductionApp/><TerminalEnhancements/></>);
