import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../slices/authSlice'
import todosReducer from '../slices/todosSlice'
import simulationsReducer from '../slices/simulationsSlice'
import presetsReducer from '../slices/presetsSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    todos: todosReducer,
    simulations: simulationsReducer,
    presets: presetsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

