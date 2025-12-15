import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../slices/authSlice'
import todosReducer from '../slices/todosSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    todos: todosReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

