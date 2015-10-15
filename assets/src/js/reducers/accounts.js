import { ActionTypes } from '../constants/accounts';
import { createCRUDReducer } from './base';

const initialState = {
    isFetching: false,
    items: [],
    errors: {}
};

const mapHandlersToActions = {
    [ActionTypes.GET_ACCOUNTS_REQUEST]: 'getCollectionRequest',
    [ActionTypes.GET_ACCOUNTS_RESPONSE]: 'getCollectionResponse',
    [ActionTypes.GET_ACCOUNTS_FAILED]: 'getCollectionFailed',

    [ActionTypes.CREATE_ACCOUNT_REQUEST]: 'createResourceRequest',
    [ActionTypes.CREATE_ACCOUNT_RESPONSE]: 'createResourceResponse',
    [ActionTypes.CREATE_ACCOUNT_FAILED]: 'createResourceFailed',

    [ActionTypes.EDIT_ACCOUNT_REQUEST]: 'editResourceRequest',
    [ActionTypes.EDIT_ACCOUNT_RESPONSE]: 'editResourceResponse',
    [ActionTypes.EDIT_ACCOUNT_FAILED]: 'editResourceFailed',

    [ActionTypes.REMOVE_ACCOUNT_REQUEST]: 'removeResourceRequest',
    [ActionTypes.REMOVE_ACCOUNT_RESPONSE]: 'removeResourceResponse',
    [ActionTypes.REMOVE_ACCOUNT_FAILED]: 'removeResourceFailed'
};

const accounts = createCRUDReducer(initialState, mapHandlersToActions, {
    getCollectionResponse: (state, action) => Object.assign({}, state, {
        isFetching: false, items: [...action.json.accounts], errors: {} }),
    createResourceResponse: (state, action) => Object.assign({}, state, {
        isFetching: false, items: [...state.items, action.json.account], errors: {} }),
    editResourceResponse: (state, action) => Object.assign({}, state, {
        isFetching: false,
        items: state.items.map(account =>
            account.id === action.json.account.id ?
                Object.assign({}, account, action.json.account) : account),
        errors: {}
    }),
    removeResourceResponse: (state, action) => Object.assign({
        isFetching: false,
        items: state.items.filter(account =>
            account.id !== action.account.id
        ),
        errors: {}
    })
});

export default accounts;
