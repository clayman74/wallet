import { combineReducers } from 'redux';
import { routerStateReducer } from 'redux-router';

import session from './session';
import accounts from './accounts';
import categories from './categories';
import transactions from './transactions';


const rootReducer = combineReducers({
    router: routerStateReducer, session, accounts, categories, transactions
});

export default rootReducer;
